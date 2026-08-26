"""Small shared hash-addressed atomic file publication primitive."""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
from pathlib import Path, PurePosixPath


SAFE_ID_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


class VaultFileUnavailable(ValueError):
    pass


class VaultFileIntegrityError(ValueError):
    pass


def publish_hash_addressed_bytes(
    storage_dir: Path,
    path_parts: tuple[str, ...],
    suffix: str,
    content: bytes,
    *,
    expected_sha256: str,
    max_bytes: int,
) -> tuple[Path, str, int]:
    if (
        not path_parts
        or any(
            not isinstance(part, str)
            or not part
            or any(character not in SAFE_ID_CHARACTERS for character in part)
            for part in path_parts
        )
        or not suffix
        or any(character not in SAFE_ID_CHARACTERS for character in suffix)
    ):
        raise ValueError("unsafe export identity")
    size = len(content)
    if size <= 0 or size > max_bytes:
        raise ValueError("export size limit exceeded")
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError("export digest mismatch")
    root = storage_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = root.joinpath(*path_parts)
    directory.mkdir(parents=True, exist_ok=True)
    directory = directory.resolve()
    if not directory.is_relative_to(root):
        raise ValueError("export path escapes storage root")
    target = directory / f"{expected_sha256}.{suffix}"
    if target.exists():
        if target.is_symlink() or target.stat().st_size != size:
            raise ValueError("existing export identity mismatch")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError("existing export digest mismatch")
        return target, target.relative_to(root).as_posix(), size
    temporary = directory / f".{expected_sha256}.{secrets.token_hex(8)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            descriptor = None
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return target, target.relative_to(root).as_posix(), size


def read_verified_vault_bytes(
    storage_dir: Path,
    vault_key: str,
    *,
    expected_sha256: str,
    expected_size: int,
    max_bytes: int,
) -> bytes:
    """Read one regular vault file through a no-follow descriptor chain."""

    relative = PurePosixPath(vault_key)
    parts = relative.parts
    if (
        not isinstance(vault_key, str)
        or not parts
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise VaultFileUnavailable("unsafe vault key")
    if (
        not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size <= 0
        or expected_size > max_bytes
        or not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
    ):
        raise VaultFileIntegrityError("invalid vault metadata")

    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise VaultFileUnavailable("no-follow file opens are unavailable")
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | no_follow | close_on_exec
    file_flags = (
        os.O_RDONLY | os.O_NONBLOCK | no_follow | close_on_exec
    )
    descriptors: list[int] = []
    try:
        current = os.open(storage_dir, directory_flags)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, directory_flags, dir_fd=current)
            descriptors.append(current)
        file_descriptor = os.open(parts[-1], file_flags, dir_fd=current)
        descriptors.append(file_descriptor)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise VaultFileUnavailable("vault target is not a regular file")
        if before.st_size != expected_size:
            raise VaultFileIntegrityError("vault size mismatch")

        chunks: list[bytes] = []
        remaining = expected_size + 1
        while remaining:
            chunk = os.read(file_descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(file_descriptor)
        if (
            len(content) != expected_size
            or after.st_size != before.st_size
            or after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or hashlib.sha256(content).hexdigest() != expected_sha256
        ):
            raise VaultFileIntegrityError("vault content mismatch")
        return content
    except (VaultFileIntegrityError, VaultFileUnavailable):
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise VaultFileUnavailable("vault file is unavailable") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
