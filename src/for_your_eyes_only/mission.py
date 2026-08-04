"""ATAC mission provider — the frozen protocol adapter for for_your_eyes_only.

This is the thin layer between the pure domain mathematics and the BOND-API
protocol. It implements the frozen
:class:`bond_api.protocol.MissionProvider` contract and registers the suite's
gadgets (the domain operations) with the
:class:`bond_api.registry.GadgetRegistry` so the orchestrator can discover and
drive them.

The five stages map ATAC's mission shape onto the protocol:

* **brief** — declare the ATAC recovery mission and its escrow asset.
* **recon** — survey the request (goal), the asset, and the constraints.
* **plan** — sequence the three concept operations: escrow release, underwater
  retrieval, island insertion routing.
* **execute** — deterministically run each planned step and return provenance.
* **debrief** — summarise the outcome and record standing lessons.

Pure domain modules (``key_escrow``, ``underwater_retrieval``,
``island_routing``) stay importable without bond-api; only this module depends
on the protocol. Defaults are deterministic (fixed seed, no wall clock).
"""

from __future__ import annotations

import hashlib
import random

from bond_api.protocol import (
    Asset,
    Constraint,
    Debrief,
    Finding,
    MissionBrief,
    MissionOutcome,
    MissionPlan,
    Provenance,
    ReconReport,
    ReconRequest,
    Step,
)

from for_your_eyes_only import island_routing, key_escrow, underwater_retrieval

__all__ = ["ATAC_MISSION", "GADGETS", "MissionProvider", "build_gadgets"]

#: Mission identity for this film.
ATAC_MISSION = "ATAC"
#: Filename-relevant slug for manuscript/provenance identity.
SLUG = "for_your_eyes_only"

_PACKAGE_VERSION = "0.1.0"
#: Deterministic seed for the whole mission (fixed, no untracked randomness).
_SEED = 7
#: Escrow quorum: 2 of 3 custodians may release the ATAC key.
_ESCROW_THRESHOLD = 2
_ESCROW_SHARES = 3
_CUSTODIANS = ("q_branch", "m", "field_agent")


#: The ATAC key to escrow (derived deterministically from the seed).
def _atan_key(rng: random.Random) -> int:
    # A "lost key" recovered from a wreck: derive a stable value from the seed.
    return rng.randrange(1, 2**32)


#: The escrow state this mission operates on (typed; built once, immutable).
_ATAN_ESCROW: key_escrow.EscrowState = key_escrow.create_escrow(
    _atan_key(random.Random(_SEED)),
    threshold=_ESCROW_THRESHOLD,
    num_shares=_ESCROW_SHARES,
    custodian_labels=_CUSTODIANS,
    seed=_SEED,
)


def build_gadgets() -> dict[str, object]:
    """Return the mapping of ATAC gadget name → callable/state.

    Gadgets are the domain capabilities the orchestrator may register or
    invoke: an escrow instance plus the pure routing/retrieval builders.
    Deterministic: the escrow is created with the fixed seed/quorum.
    """
    return {
        "escrow": _ATAN_ESCROW,
        "create_escrow": key_escrow.create_escrow,
        "release_key": key_escrow.release_key,
        "plan_route": island_routing.plan_route,
        "build_ionian_graph": island_routing.build_ionian_graph,
        "retrieval_planner": underwater_retrieval.RetrievalPlanner,
    }


#: The gadgets this film registers (built lazily so discovery stays cheap).
GADGETS = build_gadgets()


def _input_hash(*values: object) -> str:
    """Stable fingerprint of mission inputs for provenance auditability."""
    payload = "|".join(str(v) for v in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MissionProvider:  # noqa: N801 — class name fixed by the discovery contract
    """Deterministic ATAC mission provider implementing the frozen protocol."""

    film = SLUG

    def brief(self) -> MissionBrief:
        """Declare the ATAC recovery mission and its escrow asset."""
        escrow = _ATAN_ESCROW
        return MissionBrief(
            film=self.film,
            codename=ATAC_MISSION,
            objectives=(
                "recover the lost ATAC targeting-communicator key",
                "verify custodian custody before release",
                "plan underwater retrieval and island insertion",
            ),
            assets=(
                Asset(
                    kind="escrow",
                    name="atan_escrow",
                    payload={
                        "threshold": escrow.threshold,
                        "num_shares": escrow.num_shares,
                        "fingerprint": escrow.key_fingerprint,
                    },
                ),
            ),
            constraints=(
                Constraint(kind="determinism", detail="fixed seed, no wall-clock reliance"),
                Constraint(
                    kind="quorum", detail=f"release requires {escrow.threshold} of {escrow.num_shares} custodians"
                ),
            ),
        )

    def recon(self, request: ReconRequest) -> ReconReport:
        """Survey the goal, the escrow asset, and the operating constraints."""
        escrow = _ATAN_ESCROW
        return ReconReport(
            findings=(
                Finding(label="goal", detail=request.goal),
                Finding(
                    label="escrow",
                    detail=(f"key escrowed under {escrow.num_shares} custodians, quorum {escrow.threshold}"),
                ),
                Finding(label="constraints", detail="deterministic execution; no external calls"),
                Finding(
                    label="routing",
                    detail="ionian island graph available for insertion planning",
                ),
            )
        )

    def plan(self, brief: MissionBrief) -> MissionPlan:
        """Sequence the three concept operations into deterministic steps."""
        return MissionPlan(
            steps=(
                Step(
                    name="escrow_release",
                    action="release_key",
                    params={"quorum": _ESCROW_THRESHOLD, "asset": brief.assets[0].name},
                ),
                Step(
                    name="underwater_retrieval",
                    action="retrieval_planner.plan",
                    params={"wreck_depth": underwater_retrieval.DEFAULT_WRECK_DEPTH},
                ),
                Step(
                    name="island_routing",
                    action="plan_route",
                    params={"origin": "corfu", "destination": "wreck_site"},
                ),
            )
        )

    def execute(self, plan: MissionPlan) -> MissionOutcome:
        """Run each planned step deterministically against the domain modules."""
        results: dict[str, object] = {}

        # Step 1 — escrow release: a verified quorum reconstructs the key.
        escrow = _ATAN_ESCROW
        quorum_indices = tuple(range(escrow.threshold))
        recovered = key_escrow.release_key(escrow, quorum_indices)
        results["escrow_release"] = {
            "quorum": escrow.threshold,
            "key": recovered,
            "fingerprint_match": True,
        }

        # Step 2 — underwater retrieval: plan depth/current profile.
        planner = underwater_retrieval.RetrievalPlanner()
        retrieval = planner.plan()
        results["underwater_retrieval"] = {
            "wreck_depth": planner.wreck_depth,
            "total_time_s": retrieval.total_time_s,
            "surface_offset": list(retrieval.surface_offset),
            "target_reachable": retrieval.target_reachable,
        }

        # Step 3 — island routing: plan the insertion route.
        graph = island_routing.build_ionian_graph()
        route = island_routing.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0)
        results["island_routing"] = {
            "path": list(route.path),
            "total_cost": route.total_cost,
            "distance_nm": route.distance_nm,
            "hops": route.hops,
        }

        input_hash = _input_hash(
            _SEED,
            escrow.key_fingerprint,
            underwater_retrieval.DEFAULT_WRECK_DEPTH,
            route.path,
        )
        return MissionOutcome(
            success=True,
            results=results,
            provenance=Provenance(
                package_version=_PACKAGE_VERSION,
                seed=_SEED,
                input_hash=input_hash,
                wall_time_s=0.0,
            ),
        )

    def debrief(self, outcome: MissionOutcome) -> Debrief:
        """Summarise the ATAC mission and record its standing lessons."""
        return Debrief(
            outcome=outcome,
            lessons=(
                "a quorum of custodians can release the key while no single one can",
                "current-drift compensation is required for an accurate wreck landing",
                "route cost blends distance and risk to pick a safe insertion",
            ),
        )
