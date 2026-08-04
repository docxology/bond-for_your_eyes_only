"""Shared bootstrap + mission runner for ATAC scripts.

Thin helpers keep every mission-phase CLI tiny: each script calls
:func:`run_phase` which loads the provider and prints the phase result as
deterministic JSON. No business logic lives here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure the package's src/ is importable when run from the repo root.
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PACKAGE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))  # noqa: E402 - needed before package import


def load_provider() -> Any:
    """Import and return the ATAC MissionProvider (cheap, local import)."""
    from for_your_eyes_only.mission import MissionProvider

    return MissionProvider()


def print_json(payload: dict[str, Any]) -> None:
    """Print ``payload`` as sorted, indented, deterministic JSON."""
    print(json.dumps(payload, sort_keys=True, indent=2, default=str))


def run_phase(phase: str, goal: str = "recover the lost ATAC device") -> dict[str, Any]:
    """Run one phase of the ATAC mission and return its payload dict."""
    from bond_api.protocol import ReconRequest, run_mission

    provider = load_provider()
    if phase == "brief":
        brief = provider.brief()
        return {
            "film": provider.film,
            "codename": brief.codename,
            "objectives": list(brief.objectives),
            "assets": [{"kind": a.kind, "name": a.name, "payload": a.payload} for a in brief.assets],
            "constraints": [{"kind": c.kind, "detail": c.detail} for c in brief.constraints],
        }
    if phase == "recon":
        report = provider.recon(ReconRequest(goal=goal))
        return {"goal": goal, "findings": [{"label": f.label, "detail": f.detail} for f in report.findings]}
    if phase == "plan":
        plan = provider.plan(provider.brief())
        return {"steps": [{"name": s.name, "action": s.action, "params": s.params} for s in plan.steps]}
    if phase == "execute":
        debrief = run_mission(provider, ReconRequest(goal=goal))
        outcome = debrief.outcome
        return {
            "success": outcome.success,
            "results": outcome.results,
            "provenance": {
                "package_version": outcome.provenance.package_version,
                "seed": outcome.provenance.seed,
                "input_hash": outcome.provenance.input_hash,
            },
        }
    if phase == "debrief":
        debrief = run_mission(provider, ReconRequest(goal=goal))
        return {"success": debrief.outcome.success, "lessons": list(debrief.lessons)}
    raise ValueError(f"unknown phase: {phase!r}")


def main(argv: list[str] | None = None) -> int:
    """Entry point for a phase CLI: ``python scripts/<phase>.py [goal]``."""
    argv = list(sys.argv[1:] if argv is None else argv)
    phase = Path(sys.argv[0]).stem  # brief/recon/plan/execute/debrief
    goal = argv[0] if argv else "recover the lost ATAC device"
    try:
        print_json(run_phase(phase, goal))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
