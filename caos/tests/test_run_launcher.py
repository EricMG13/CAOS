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


def test_cpdr_settings_are_disabled_and_deny_all_by_default(monkeypatch) -> None:
    for name in (
        "ANTHROPIC_API_KEY",
        "CANONICAL_AGENT_ENABLED",
        "CPDR_AGENT_ENABLED",
        "CPDR_PILOT_CASE_IDS",
        "CPDR_PILOT_SUBJECTS",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.anthropic_api_key == ""
    assert settings.canonical_agent_enabled is False
    assert settings.cpdr_agent_enabled is False
    assert settings.cpdr_pilot_case_ids == ()
    assert settings.cpdr_pilot_subjects == ()


def test_cpdr_settings_parse_strict_flag_and_bounded_exact_allowlists(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setenv("CANONICAL_AGENT_ENABLED", "true")
    monkeypatch.setenv("CPDR_AGENT_ENABLED", "true")
    monkeypatch.setenv("CPDR_PILOT_CASE_IDS", "case-1, case-2,case-1")
    monkeypatch.setenv("CPDR_PILOT_SUBJECTS", "analyst@example.com")
    settings = Settings.from_env()
    assert settings.anthropic_api_key == "secret"
    assert settings.canonical_agent_enabled is True
    assert settings.cpdr_agent_enabled is True
    assert settings.cpdr_pilot_case_ids == ("case-1", "case-2")
    assert settings.cpdr_pilot_subjects == ("analyst@example.com",)


@pytest.mark.parametrize("value", ["1", "TRUE", "yes", "False"])
def test_cpdr_settings_reject_noncanonical_boolean(monkeypatch, value: str) -> None:
    monkeypatch.setenv("CPDR_AGENT_ENABLED", value)
    with pytest.raises(ValueError, match="CPDR_AGENT_ENABLED must be true or false"):
        Settings.from_env()


@pytest.mark.parametrize("value", ["1", "TRUE", "yes", "False"])
def test_canonical_settings_reject_noncanonical_boolean(monkeypatch, value: str) -> None:
    monkeypatch.setenv("CANONICAL_AGENT_ENABLED", value)
    with pytest.raises(ValueError, match="CANONICAL_AGENT_ENABLED must be true or false"):
        Settings.from_env()
