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


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_regenerating_the_artifact_tree_is_byte_identical(tmp_path):
    """The determinism claim, verified end to end by real regeneration.

    This is the test whose absence let the claim stand while being false: the
    only determinism coverage was `generate_variables(now=<fixed>)`, which
    pinned the timestamp it was supposed to be checking. Running the real
    orchestrator twice into two roots and diffing every byte — JSON, resolved
    manuscript sections, and the four PNGs — is the claim as stated.
    """
    first, second = tmp_path / "run_a", tmp_path / "run_b"
    for root in (first, second):
        proc = _run_script("z_generate_manuscript_variables.py", "--output-root", str(root))
        assert proc.returncode == 0, proc.stdout + proc.stderr

    a, b = _tree_bytes(first), _tree_bytes(second)
    assert sorted(a) == sorted(b)
    assert len(a) >= 14, f"expected the full artifact set, got {sorted(a)}"
    differing = sorted(name for name in a if a[name] != b[name])
    assert differing == [], f"regeneration is not byte-identical: {differing}"


def test_no_wall_clock_value_reaches_a_persisted_artifact(tmp_path):
    """Negative control for the determinism fix: today's date must not appear.

    A regeneration could be byte-identical within one second and still be
    wall-clock-derived. The build stamp is the declared `paper.date`, so unless
    that happens to be today, the current date must be absent from the tree.
    """
    import datetime as _dt

    from for_your_eyes_only import manuscript_variables as mv

    config = mv.load_manuscript_config(PACKAGE_ROOT / "manuscript" / "config.yaml")
    declared = str(config["paper"]["date"])
    today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    if today == declared:
        pytest.skip("declared paper.date is today; the control cannot distinguish the two")

    root = tmp_path / "run"
    proc = _run_script("z_generate_manuscript_variables.py", "--output-root", str(root))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    hits = [name for name, blob in _tree_bytes(root).items() if today.encode() in blob]
    assert hits == [], f"wall-clock date {today} leaked into persisted artifacts: {hits}"
    # ...and the deterministic stamp really is in there, so the check above is
    # not passing merely because no date is written at all.
    assert any(declared.encode() in blob for blob in _tree_bytes(root).values())


def test_source_date_epoch_overrides_the_declared_date(tmp_path):
    """The reproducible-builds override is honoured (and is a real seam)."""
    root = tmp_path / "run"
    proc = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_ROOT / "scripts" / "z_generate_manuscript_variables.py"),
            "--output-root",
            str(root),
        ],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "SOURCE_DATE_EPOCH": "1000000000"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads((root / "data" / "manuscript_variables.json").read_text(encoding="utf-8"))
    assert data["SOURCE_DATE"] == "2001-09-09T01:46:40+00:00"


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
