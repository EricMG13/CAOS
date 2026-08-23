from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from caos.config import Settings


@pytest.mark.parametrize("value", ["-1", "65536"])
def test_settings_rejects_out_of_range_listener_port(monkeypatch, value: str) -> None:
    monkeypatch.setenv("PORT", value)
    with pytest.raises(ValueError, match="PORT must be between 0 and 65535"):
        Settings.from_env()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("MAX_UPLOAD_MB", "0", "MAX_UPLOAD_MB must be greater than 0"),
        ("MAX_UPLOAD_MB", "-1", "MAX_UPLOAD_MB must be greater than 0"),
        ("CLAMAV_PORT", "0", "CLAMAV_PORT must be between 1 and 65535"),
        ("CLAMAV_PORT", "65536", "CLAMAV_PORT must be between 1 and 65535"),
    ],
)
def test_settings_rejects_invalid_upload_and_scanner_limits(monkeypatch, name: str, value: str, message: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message):
        Settings.from_env()


def test_run_launcher_honors_port_environment(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("PORT", "8011")
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=lambda *args, **kwargs: calls.append((args, kwargs))))

    runpy.run_path(Path(__file__).parents[1] / "server" / "run.py", run_name="__main__")

    assert calls[0][1]["host"] == "0.0.0.0"
    assert calls[0][1]["port"] == 8011
