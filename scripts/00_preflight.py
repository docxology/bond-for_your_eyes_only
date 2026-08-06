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
    import os as _os

    from bond_api.protocol import MissionProvider, ReconRequest, run_mission
    from for_your_eyes_only import underwater_retrieval as uw
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

    # Retrieval plan is reachable and within the operational endurance ceiling.
    # The dive verdict is deliberately failable: any plan whose total time is
    # non-positive or exceeds the declared endurance ceiling is a planning
    # failure, not an unconditional pass. An environment seam overrides the
    # bottom time (mirroring the SOURCE_DATE_EPOCH precedent) so a test can
    # drive the verdict red without a mocking framework.
    seam = _os.environ.get("ATAC_PREFLIGHT_BOTTOM_TIME_S")
    bottom_time = float(seam) if seam is not None else uw.RetrievalPlanner().bottom_time_s
    planner = uw.RetrievalPlanner(bottom_time_s=bottom_time)
    plan = planner.plan()
    verdicts.append(("target_reachable", plan.target_reachable is True))
    verdicts.append(("finite_dive_time", 0.0 < plan.total_time_s <= uw.MAX_TOTAL_DIVE_TIME_S))

    # Custody chain: the escrow carries a real handoff ledger and it verifies
    # (recomputed in the mission, surfaced here as a pass/fail verdict).
    verdicts.append(("custody_chain", results["escrow_release"]["custody_chain_ok"] is True))

    for name, ok in verdicts:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(ok for _name, ok in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
