"""ATAC preflight: verify the mission can run end-to-end before scripting.

Thin orchestrator. Runs the full five-stage flow and prints 0/1 verdicts;
exits 0 iff every verdict passes (protocol conformance, escrow recovery,
routing, retrieval reachability).
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PACKAGE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    from bond_api.protocol import MissionProvider, ReconRequest, run_mission
    from for_your_eyes_only import underwater_retrieval
    from for_your_eyes_only.mission import MissionProvider as ATACProvider

    provider = ATACProvider()
    verdicts: list[tuple[str, bool]] = []

    # Protocol conformance (runtime-checkable).
    verdicts.append(("protocol_conformance", isinstance(provider, MissionProvider)))

    # Full mission flow executes and succeeds.
    debrief = run_mission(provider, ReconRequest(goal="recover the lost ATAC device"))
    verdicts.append(("mission_success", debrief.outcome.success))
    results = debrief.outcome.results
    verdicts.append(("escrow_released", results["escrow_release"]["fingerprint_match"] is True))

    # Routing produces a connected insertion route.
    route = results["island_routing"]
    verdicts.append(("route_connected", len(route["path"]) >= 2))
    verdicts.append(("route_reaches_wreck", route["path"][-1] == "wreck_site"))

    # Retrieval plan is reachable.
    planner = underwater_retrieval.RetrievalPlanner()
    plan = planner.plan()
    verdicts.append(("target_reachable", plan.target_reachable is True))
    verdicts.append(("finite_dive_time", plan.total_time_s > 0))

    for name, ok in verdicts:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(ok for _name, ok in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
