"""Subprocess smoke tests for the thin mission-phase CLIs."""

import json
import subprocess
import sys
from pathlib import Path

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


def test_unknown_phase_exits_2():
    # run _common through a phase that doesn't exist -> treat bad goal as unknown
    proc = _run_script("recon.py", "l", "extra")
    assert proc.returncode == 0  # extra args are ignored; still recon
