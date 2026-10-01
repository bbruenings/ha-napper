"""Tests for the manifest, strings, services.yaml and hacs.json health."""

import json
import os
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CC = REPO / "custom_components" / "napper"


def test_manifest_json_valid_and_consistent():
    manifest = json.loads((CC / "manifest.json").read_text())
    assert manifest["domain"] == "napper"
    assert manifest["config_flow"] is True
    assert "@bbruenings" in manifest["codeowners"]
    assert manifest["documentation"].startswith("https://github.com/bbruenings/ha-napper")
    assert manifest["issue_tracker"] == "https://github.com/bbruenings/ha-napper/issues"


def test_strings_json_valid():
    strings = json.loads((CC / "strings.json").read_text())
    steps = strings["config"]["step"]
    for step in ("user", "otp", "baby", "reauth_confirm"):
        assert step in steps, f"missing config step {step}"
    errors = strings["config"]["error"]
    # errors the config flow can raise must be translatable
    for key in ("invalid_email", "email_required", "invalid_otp", "otp_required",
                "connection_error", "timeout", "invalid_token", "baby_required"):
        assert key in errors, f"missing error string {key}"
    aborts = strings["config"]["abort"]
    for key in ("already_configured", "no_babies", "auth_failed", "reauth_successful"):
        assert key in aborts, f"missing abort string {key}"


def test_services_yaml_valid_and_complete():
    services = yaml.safe_load((CC / "services.yaml").read_text())
    expected = {
        "log_diaper_change",
        "log_solid_food",
        "log_solids",
        "log_sleep_start",
        "log_sleep_end",
        "log_wake_up",
        "log_bedtime",
        "log_nursing",
        "delete_log",
        "get_logs",
    }
    assert set(services) == expected, f"services.yaml mismatch: {set(services) ^ expected}"


def test_hacs_json_valid():
    hacs = json.loads((REPO / "hacs.json").read_text())
    assert hacs["name"] == "Napper Baby Tracking"
    assert hacs["render_readme"] is True


def test_no_pycache_committed():
    """__pycache__ is gitignored; also assert it is not tracked by git."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO
    ).stdout.splitlines()
    offenders = [f for f in tracked if "__pycache__" in f or f.endswith(".pyc")]
    assert not offenders, f"bytecode tracked in git: {offenders}"


def test_readme_mentions_integration_domain():
    readme = (REPO / "README.md").read_text()
    assert "ha-napper" in readme
    assert "HACS" in readme


def test_services_registered_match_services_yaml():
    """Every service registered in services.py is described in services.yaml."""
    import re

    source = (CC / "services.py").read_text()
    registered = set(re.findall(r'\basync_register\s*\([^)]*?"([a-z_]+)"', source, re.S))
    services = yaml.safe_load((CC / "services.yaml").read_text())
    missing = registered - set(services)
    assert not missing, f"registered but not documented: {missing}"
    extra = set(services) - registered
    assert not extra, f"documented but not registered: {extra}"


def test_issue_templates_reference_correct_repo():
    for template in ("bug_report.yml", "feature_request.yml"):
        text = (REPO / ".github" / "ISSUE_TEMPLATE" / template).read_text()
        assert "ha-inlite" not in text, f"{template} still references ha-inlite"