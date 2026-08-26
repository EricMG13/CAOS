#!/usr/bin/env python3
"""Deterministically refresh the declared Deploy V manifest and integrity hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = (
    Path(__file__).resolve().parents[1]
    / "server"
    / "caos"
    / "methodology"
    / "vendor"
    / "deploy_v"
)
MANIFEST = "DEPLOY_V_MANIFEST.json"
INTEGRITY = "DEPLOY_V_INTEGRITY_v1.json"


class RegenerationError(ValueError):
    pass


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RegenerationError(f"authority file must be a regular file: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegenerationError(f"cannot read authority file: {path.name}") from exc
    if not isinstance(value, dict):
        raise RegenerationError(f"authority file must contain an object: {path.name}")
    return value


def _safe_declared_file(root: Path, folder_slug: str, relative: str) -> Path:
    folder = PurePosixPath(folder_slug)
    child = PurePosixPath(relative)
    if (
        folder.is_absolute()
        or child.is_absolute()
        or ".." in folder.parts
        or ".." in child.parts
        or not folder.parts
        or not child.parts
    ):
        raise RegenerationError(f"unsafe declared path: {folder_slug}/{relative}")
    skills_root = root / "skills"
    candidate = skills_root.joinpath(*folder.parts, *child.parts)
    current = skills_root
    for part in (*folder.parts, *child.parts):
        current = current / part
        if current.is_symlink():
            raise RegenerationError(
                f"declared path must not traverse a symlink: {folder_slug}/{relative}"
            )
    try:
        candidate.resolve(strict=True).relative_to(skills_root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise RegenerationError(
            f"declared file escapes or is missing: {folder_slug}/{relative}"
        ) from exc
    if not candidate.is_file():
        raise RegenerationError(
            f"declared path must be a regular file: {folder_slug}/{relative}"
        )
    return candidate


def _refresh_skills(root: Path, skills: list[dict[str, Any]]) -> None:
    for skill in skills:
        folder_slug = skill.get("folder_slug")
        declared = skill.get("relative_file_hashes")
        if not isinstance(folder_slug, str) or not isinstance(declared, dict):
            raise RegenerationError("invalid skill integrity entry")
        refreshed: dict[str, dict[str, Any]] = {}
        for relative in sorted(declared):
            if not isinstance(relative, str):
                raise RegenerationError("declared file path must be a string")
            payload = _safe_declared_file(root, folder_slug, relative).read_bytes()
            refreshed[relative] = {"bytes": len(payload), "sha256": _sha256(payload)}
        entry = refreshed.get("SKILL.md")
        if entry is None:
            raise RegenerationError(f"{folder_slug}: SKILL.md must be declared")
        skill["relative_file_hashes"] = refreshed
        skill["entry_bytes"] = entry["bytes"]
        skill["entry_sha256"] = entry["sha256"]


def _build_id(integrity: dict[str, Any]) -> str:
    identity = {
        "authority": integrity["authority"],
        "routing_index": integrity["routing_index"],
        "schema_version": integrity["schema_version"],
        "skills": integrity["skills"],
        "source_hashes": integrity["source_hashes"],
    }
    return _sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def regenerate(root: Path) -> tuple[bytes, bytes]:
    root = root.resolve(strict=True)
    manifest = _read_json(root / MANIFEST)
    integrity = _read_json(root / INTEGRITY)
    manifest_skills = manifest.get("skills")
    integrity_skills = integrity.get("skills")
    if not isinstance(manifest_skills, list) or not isinstance(integrity_skills, list):
        raise RegenerationError("authority skills must be lists")
    if [item.get("folder_slug") for item in manifest_skills] != [
        item.get("folder_slug") for item in integrity_skills
    ]:
        raise RegenerationError("manifest and integrity skill order differs")
    for manifest_skill, integrity_skill in zip(
        manifest_skills, integrity_skills, strict=True
    ):
        if set(manifest_skill.get("relative_file_hashes", {})) != set(
            integrity_skill.get("relative_file_hashes", {})
        ):
            raise RegenerationError(
                f"declared files differ for {manifest_skill.get('folder_slug')}"
            )
    _refresh_skills(root, manifest_skills)
    _refresh_skills(root, integrity_skills)
    manifest_payload = _json_bytes(manifest)
    source_files = {
        "deployed_baseline": "DEPLOY_V_BASELINE.json",
        "deployed_child_schema_registry": "CP_DEPLOY_V_CHILD_SCHEMA_REGISTRY_v1.json",
    }
    source_hashes = integrity.get("source_hashes")
    if not isinstance(source_hashes, dict):
        raise RegenerationError("integrity source_hashes must be an object")
    for key, filename in source_files.items():
        path = root / filename
        if path.is_symlink() or not path.is_file():
            raise RegenerationError(f"source authority must be a regular file: {filename}")
        source_hashes[key] = _sha256(path.read_bytes())
    source_hashes["deployed_manifest"] = _sha256(manifest_payload)
    integrity["build_id"] = _build_id(integrity)
    return manifest_payload, _json_bytes(integrity)


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest, integrity = regenerate(args.root)
        current_manifest = (args.root / MANIFEST).read_bytes()
        current_integrity = (args.root / INTEGRITY).read_bytes()
        if args.check:
            if current_manifest != manifest or current_integrity != integrity:
                raise RegenerationError("Deploy V authority hashes are stale")
            return 0
        _atomic_write(args.root / MANIFEST, manifest)
        _atomic_write(args.root / INTEGRITY, integrity)
    except (OSError, RegenerationError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
