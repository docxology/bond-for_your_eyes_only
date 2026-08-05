"""Subprocess smoke tests for the thin mission-phase CLIs."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PACKAGE_ROOT / "scripts" / script), *args],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_brief_prints_valid_json():
    proc = _run_script("brief.py")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["codename"] == "ATAC"
    assert "objectives" in data and len(data["objectives"]) >= 2


def test_recon_prints_findings():
    proc = _run_script("recon.py", "recover the lost ATAC device")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["goal"] == "recover the lost ATAC device"
    assert len(data["findings"]) >= 3


def test_plan_prints_steps():
    proc = _run_script("plan.py")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    actions = [s["action"] for s in data["steps"]]
    assert actions == [
        "release_key",
        "recover_erasure",
        "retrieval_planner.plan",
        "plan_route",
        "intercept_solution",
        "compute_link_budget",
    ]


def test_execute_prints_outcome():
    proc = _run_script("execute.py")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert data["results"]["island_routing"]["path"][-1] == "wreck_site"
    assert data["results"]["acoustic_link"]["closes"] is True
    assert data["results"]["targeting"]["feasible"] is True


def test_debrief_prints_lessons():
    proc = _run_script("debrief.py")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert len(data["lessons"]) == 3


def test_preflight_all_pass():
    proc = _run_script("00_preflight.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_extra_cli_args_are_ignored():
    """Only the first positional arg is the goal; trailing args do not break the CLI."""
    proc = _run_script("recon.py", "primary goal", "ignored extra")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["goal"] == "primary goal"


def test_unknown_phase_raises():
    """run_phase rejects a phase outside the frozen five-stage protocol."""
    import sys as _sys

    _sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))
    import _common

    with pytest.raises(ValueError, match="unknown phase"):
        _common.run_phase("infiltrate")


def test_unknown_phase_cli_exits_2(tmp_path):
    """A phase CLI whose filename is not a protocol stage exits 2, not 0.

    The script name *is* the phase, so a copy under an unknown name is the
    realistic way this failure reaches the CLI layer.
    """
    bogus = tmp_path / "infiltrate.py"
    bogus.write_text(
        (PACKAGE_ROOT / "scripts" / "recon.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(bogus)],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(PACKAGE_ROOT / "scripts")},
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "unknown phase" in proc.stderr
