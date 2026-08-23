from __future__ import annotations

import os
import subprocess
from pathlib import Path


DEPLOY = Path(__file__).parents[1] / "deploy"


def _fake_docker(tmp_path: Path) -> tuple[dict[str, str], Path]:
    docker = tmp_path / "docker"
    docker.write_text(
        """#!/bin/sh
printf '%s\\n' "$*" >> "$DOCKER_LOG"
case "$*" in
    *pg_dump*) printf 'new-dump\\n' ;;
    *"volume ls"*) printf 'vault-volume\\n' ;;
    *"tar -C"*) printf 'new-vault\\n' ;;
    *"volume inspect"*) exit 1 ;;
    *"SELECT EXISTS"*) printf 'f\\n' ;;
esac
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "DOCKER_LOG": str(log)}, log


def _checksum(path: Path) -> str:
    return subprocess.run(["cksum"], input=path.read_bytes(), capture_output=True, check=True).stdout.decode().strip()


def test_backup_serializes_publishers_and_writes_pair_manifest(tmp_path: Path) -> None:
    env, log = _fake_docker(tmp_path)
    output = tmp_path / "backup"
    output.mkdir()
    lock = output / ".caos-backup.lock"
    lock.mkdir()

    blocked = subprocess.run([str(DEPLOY / "backup.sh"), str(output)], env=env, capture_output=True, text=True, check=False)
    assert blocked.returncode == 75
    assert "lock requires operator review" in blocked.stderr
    assert not log.exists()

    lock.rmdir()
    succeeded = subprocess.run([str(DEPLOY / "backup.sh"), str(output)], env=env, capture_output=True, text=True, check=False)
    assert succeeded.returncode == 0
    assert (output / "caos.backup.manifest").read_text(encoding="utf-8").splitlines() == [f"caos.dump {_checksum(output / 'caos.dump')}", f"vault.tgz {_checksum(output / 'vault.tgz')}"]
    assert not (output / ".caos-backup.lock").exists()
    restored = subprocess.run([str(DEPLOY / "restore_drill.sh"), str(output / "caos.dump")], env=env, capture_output=True, text=True, check=False)
    assert restored.returncode == 0
    assert "restore drill passed" in restored.stdout


def test_backup_releases_lock_when_temporary_file_creation_fails(tmp_path: Path) -> None:
    env, log = _fake_docker(tmp_path)
    mktemp = tmp_path / "mktemp"
    mktemp.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    mktemp.chmod(0o755)
    output = tmp_path / "backup"

    result = subprocess.run([str(DEPLOY / "backup.sh"), str(output)], env=env, capture_output=True, text=True, check=False)

    assert result.returncode != 0
    assert not (output / ".caos-backup.lock").exists()
    assert not log.exists()


def test_restore_drill_rejects_mismatched_standard_backup_pair_before_side_effects(tmp_path: Path) -> None:
    env, log = _fake_docker(tmp_path)
    dump = tmp_path / "caos.dump"
    vault = tmp_path / "vault.tgz"
    dump.write_bytes(b"dump")
    vault.write_bytes(b"vault")
    (tmp_path / "caos.backup.manifest").write_text("caos.dump 0 0\nvault.tgz 0 0\n", encoding="utf-8")

    result = subprocess.run([str(DEPLOY / "restore_drill.sh"), str(dump)], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "backup manifest does not match" in result.stderr
    assert "volume create" not in log.read_text(encoding="utf-8")
