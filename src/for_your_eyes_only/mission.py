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
* **plan** — sequence the six concept operations: escrow release, erasure-coded
  key recovery, underwater retrieval, island insertion routing, fire-control
  targeting, and the acoustic uplink budget.
* **execute** — deterministically run each planned step and return provenance.
* **debrief** — summarise the outcome and record standing lessons.

All six pure domain modules (``key_escrow``, ``key_recovery``,
``underwater_retrieval``, ``island_routing``, ``targeting``,
``acoustic_link``) stay importable without bond-api; only this module depends
on the protocol. Defaults are deterministic (fixed seed, no wall clock).
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

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

from for_your_eyes_only import (
    acoustic_link,
    island_routing,
    key_escrow,
    key_recovery,
    targeting,
    underwater_retrieval,
)

__all__ = [
    "ATAC_LINK",
    "ATAC_LINK_RANGE_M",
    "ATAC_MISSION",
    "ATAC_SEA_STATE",
    "CUSTODIANS",
    "ESCROW_SHARES",
    "ESCROW_THRESHOLD",
    "GADGETS",
    "MISSION_SEED",
    "RECOVERY_CODE_SYMBOLS",
    "RECOVERY_DATA_SYMBOLS",
    "ROUTE_DESTINATION",
    "ROUTE_ORIGIN",
    "ROUTE_RISK_WEIGHT",
    "SLUG",
    "CanonicalMission",
    "MissionProvider",
    "build_gadgets",
    "canonical_mission",
    "key_fingerprint",
    "mission_succeeded",
    "recovery_code_label",
]

#: Mission identity for this film.
ATAC_MISSION = "ATAC"
#: Filename-relevant slug for manuscript/provenance identity.
SLUG = "for_your_eyes_only"

_PACKAGE_VERSION = "0.1.0"
#: Deterministic seed for the whole mission (fixed, no untracked randomness).
MISSION_SEED = 7
#: Escrow quorum: 2 of 3 custodians may release the ATAC key.
ESCROW_THRESHOLD = 2
ESCROW_SHARES = 3
CUSTODIANS = ("q_branch", "m", "field_agent")
#: Erasure-code geometry used for the recovered-key fragments.
RECOVERY_DATA_SYMBOLS = 4
RECOVERY_CODE_SYMBOLS = 6
#: Canonical Ionian insertion leg and how strongly risk penalises an edge.
ROUTE_ORIGIN = "corfu"
ROUTE_DESTINATION = "wreck_site"
ROUTE_RISK_WEIGHT = 1.0
#: Sea state assumed for the uplink's ambient-noise term (0 = glassy calm).
ATAC_SEA_STATE = 1.0
#: Acoustic link configuration for the ATAC underwater uplink. The wreck
#: uplink is a shallow-water horizontal channel (range >> depth), so it uses
#: cylindrical spreading — the exponent ``n = 1`` in ``10*n*log10(r)``, i.e.
#: 10 dB of geometric loss per decade of range. The ambient noise term is
#: computed from :data:`ATAC_SEA_STATE` rather than typed as a dB literal, so
#: ``NL`` has a stated sea state behind it. Tuned so the 3.5 km operating range
#: closes with margin and max_range is interior to the plan.
ATAC_LINK = acoustic_link.AcousticLink(
    frequency_khz=15.0,
    source_level_db=145.0,
    noise_level_db=acoustic_link.noise_level(ATAC_SEA_STATE),
    directivity_index_db=10.0,
    detection_threshold_db=8.0,
    spreading=acoustic_link.CYLINDRICAL_SPREADING,
)
#: Operating range (m) at which the link budget is evaluated (wreck uplink).
ATAC_LINK_RANGE_M = 3500.0


#: The ATAC key to escrow (derived deterministically from the seed).
def _atan_key(rng: random.Random) -> int:
    # A "lost key" recovered from a wreck: derive a stable value from the seed.
    return rng.randrange(1, key_escrow.KEY_BOUND)


def key_fingerprint(key: int) -> str:
    """Return the SHA-256 fingerprint an escrow binds a key to.

    Exposed so the mission can *re-derive* the fingerprint of a released key
    and compare it against the escrow, rather than asserting a match.
    """
    return hashlib.sha256(str(key).encode("utf-8")).hexdigest()


#: The escrow state this mission operates on (typed; built once, immutable).
#: The custody ledger over the custodians is bound to the escrow at creation,
#: so the audit trail the escrow advertises is actually carried by it.
_ATAN_CUSTODY_CHAIN: tuple[key_escrow.CustodyTransfer, ...] = key_escrow.custody_chain_for(CUSTODIANS)
_ATAN_ESCROW: key_escrow.EscrowState = key_escrow.create_escrow(
    _atan_key(random.Random(MISSION_SEED)),
    threshold=ESCROW_THRESHOLD,
    num_shares=ESCROW_SHARES,
    custodian_labels=CUSTODIANS,
    seed=MISSION_SEED,
    custody_chain=_ATAN_CUSTODY_CHAIN,
)


def build_gadgets() -> dict[str, object]:
    """Return the mapping of ATAC gadget name → callable/state.

    Gadgets are the domain capabilities the orchestrator may register or
    invoke: an escrow instance plus the pure routing/retrieval/builders.
    Deterministic: the escrow is created with the fixed seed/quorum.
    """
    return {
        "escrow": _ATAN_ESCROW,
        "create_escrow": key_escrow.create_escrow,
        "release_key": key_escrow.release_key,
        "plan_route": island_routing.plan_route,
        "build_ionian_graph": island_routing.build_ionian_graph,
        "retrieval_planner": underwater_retrieval.RetrievalPlanner,
        "targeting": targeting.intercept_solution,
        "encode_erasure": key_recovery.encode_erasure,
        "recover_erasure": key_recovery.recover_erasure,
        "erasure_code": key_recovery.ErasureCode(RECOVERY_DATA_SYMBOLS, RECOVERY_CODE_SYMBOLS),
        "acoustic_link": ATAC_LINK,
        "compute_link_budget": acoustic_link.compute_link_budget,
    }


#: The gadgets this film registers (built lazily so discovery stays cheap).
GADGETS = build_gadgets()


def _input_hash(*values: object) -> str:
    """Stable fingerprint of mission inputs for provenance auditability."""
    payload = "|".join(str(v) for v in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Canonical mission scenario (single source of truth for mission + manuscript)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CanonicalMission:
    """The deterministic ATAC mission scenario, computed once, shared everywhere.

    Both ``MissionProvider.execute`` and ``manuscript_variables`` draw from a
    single :class:`CanonicalMission` so the outcome ``results`` and the
    manuscript ``{{TOKEN}}``s can never disagree.
    """

    released_key: int
    #: Whether the released key re-derives the escrow's stored fingerprint.
    #: Computed by comparison, never asserted, so the manuscript token and the
    #: mission result both fail loudly if release ever returns a wrong key.
    fingerprint_match: bool
    escrow_threshold: int
    escrow_num_shares: int
    #: The custody chain bound to the escrow (the auditable handoff ledger).
    custody_chain: tuple[key_escrow.CustodyTransfer, ...]
    #: Whether ``custody_chain`` is a well-formed linked ledger (recomputed, not
    #: stapled): every transfer indexes consecutive, chains to its predecessor,
    #: and re-hashes to its own stored commitment.
    custody_chain_ok: bool
    custody_tip: str
    recovery_code: key_recovery.ErasureCode
    recovery_data: tuple[int, ...]
    recovery_encoded: tuple[int, ...]
    recovery_recovered: tuple[int, ...]
    retrieval: underwater_retrieval.RetrievalPlan
    route: island_routing.RoutePlan
    fire: targeting.FireControlSolution
    link_budget: acoustic_link.LinkBudget
    wreck_depth: float


def canonical_mission() -> CanonicalMission:
    """Compute the deterministic ATAC mission outputs as typed domain objects."""
    escrow_key = key_escrow.release_key(_ATAN_ESCROW, tuple(range(_ATAN_ESCROW.threshold)))
    recovery_code = key_recovery.ErasureCode(RECOVERY_DATA_SYMBOLS, RECOVERY_CODE_SYMBOLS)
    data = tuple((escrow_key + i) % key_recovery.ERASURE_PRIME for i in range(RECOVERY_DATA_SYMBOLS))
    encoded = key_recovery.encode_erasure(data, recovery_code)
    recovered = key_recovery.recover_erasure(encoded, recovery_code)
    planner = underwater_retrieval.RetrievalPlanner()
    retrieval = planner.plan()
    graph = island_routing.build_ionian_graph()
    route = island_routing.plan_route(graph, ROUTE_ORIGIN, ROUTE_DESTINATION, risk_weight=ROUTE_RISK_WEIGHT)
    fire = targeting.intercept_solution(
        target_range_m=4000.0,
        target_bearing_deg=45.0,
        target_course_deg=120.0,
        target_speed_ms=8.0,
        weapon_speed_ms=45.0,
    )
    link_budget = acoustic_link.compute_link_budget(ATAC_LINK, ATAC_LINK_RANGE_M)
    return CanonicalMission(
        released_key=escrow_key,
        fingerprint_match=key_fingerprint(escrow_key) == _ATAN_ESCROW.key_fingerprint,
        escrow_threshold=_ATAN_ESCROW.threshold,
        escrow_num_shares=_ATAN_ESCROW.num_shares,
        custody_chain=_ATAN_ESCROW.custody_chain,
        custody_chain_ok=key_escrow.custody_chain_is_consistent(_ATAN_ESCROW.custody_chain),
        custody_tip=_ATAN_ESCROW.custody_chain[-1].chain_hash if _ATAN_ESCROW.custody_chain else "",
        recovery_code=recovery_code,
        recovery_data=data,
        recovery_encoded=encoded,
        recovery_recovered=recovered,
        retrieval=retrieval,
        route=route,
        fire=fire,
        link_budget=link_budget,
        wreck_depth=underwater_retrieval.DEFAULT_WRECK_DEPTH,
    )


def recovery_code_label() -> str:
    """Return the erasure geometry as ``"k-of-n"`` — data symbols of code symbols.

    Derived from the constants rather than typed as a literal: the plan step
    previously advertised ``"6-of-4"``, which reads the geometry backwards (it
    would mean six symbols required out of four stored) and no gate caught it
    because it was a free-text string.
    """
    return f"{RECOVERY_DATA_SYMBOLS}-of-{RECOVERY_CODE_SYMBOLS}"


def mission_succeeded(scenario: CanonicalMission) -> bool:
    """Return whether every stage of ``scenario`` met its own success condition.

    This is the derivation behind :attr:`MissionOutcome.success`, which was
    previously the literal ``True``. A stapled literal made
    ``scripts/00_preflight.py``'s ``mission_success`` verdict unfalsifiable:
    no input could turn it red. Every clause below is a measured property of
    the computed scenario, so a stage that stopped working flips the verdict.
    """
    return bool(
        scenario.fingerprint_match
        and list(scenario.recovery_recovered) == list(scenario.recovery_data)
        and scenario.retrieval.target_reachable
        and scenario.route.path
        and scenario.route.path[-1] == ROUTE_DESTINATION
        and scenario.fire.feasible
        and scenario.link_budget.closes
    )


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
        """Sequence the concept operations into deterministic steps."""
        return MissionPlan(
            steps=(
                Step(
                    name="escrow_release",
                    action="release_key",
                    params={"quorum": ESCROW_THRESHOLD, "asset": brief.assets[0].name},
                ),
                Step(name="key_recovery", action="recover_erasure", params={"code": recovery_code_label()}),
                Step(
                    name="underwater_retrieval",
                    action="retrieval_planner.plan",
                    params={"wreck_depth": underwater_retrieval.DEFAULT_WRECK_DEPTH},
                ),
                Step(
                    name="island_routing",
                    action="plan_route",
                    params={"origin": ROUTE_ORIGIN, "destination": ROUTE_DESTINATION},
                ),
                Step(name="targeting", action="intercept_solution", params={"weapon_speed_ms": 45.0}),
                Step(
                    name="acoustic_link",
                    action="compute_link_budget",
                    params={"range_m": ATAC_LINK_RANGE_M, "frequency_khz": ATAC_LINK.frequency_khz},
                ),
            )
        )

    def execute(self, plan: MissionPlan) -> MissionOutcome:
        """Run each planned step deterministically against the domain modules."""
        results: dict[str, object] = {}
        sc = canonical_mission()

        # Step 1 — escrow release: a verified quorum reconstructs the key. The
        # match is re-derived from the released key, not asserted: a stapled
        # `True` here would make the preflight's escrow verdict unfalsifiable.
        escrow = _ATAN_ESCROW
        results["escrow_release"] = {
            "quorum": escrow.threshold,
            "key": sc.released_key,
            "fingerprint_match": sc.fingerprint_match,
            "custody_len": len(sc.custody_chain),
            "custody_tip": sc.custody_tip,
            "custody_chain_ok": sc.custody_chain_ok,
        }

        # Step 2 — key recovery: erasure-code reconstructs the key fragments.
        results["key_recovery"] = {
            "data_symbols": sc.recovery_code.data_symbols,
            "code_symbols": sc.recovery_code.code_symbols,
            "recovered": list(sc.recovery_recovered),
            "matches": list(sc.recovery_recovered) == list(sc.recovery_data),
        }

        # Step 3 — underwater retrieval: plan depth/current profile.
        retrieval = sc.retrieval
        results["underwater_retrieval"] = {
            "wreck_depth": sc.wreck_depth,
            "total_time_s": retrieval.total_time_s,
            "surface_offset": list(retrieval.surface_offset),
            "target_reachable": retrieval.target_reachable,
        }

        # Step 4 — island routing: plan the insertion route.
        route = sc.route
        results["island_routing"] = {
            "path": list(route.path),
            "total_cost": route.total_cost,
            "distance_nm": route.distance_nm,
            "hops": route.hops,
        }

        # Step 5 — targeting: fire-control intercept solution.
        fire = sc.fire
        results["targeting"] = {
            "intercept_time_s": fire.intercept_time_s,
            "lead_angle_deg": fire.lead_angle_deg,
            "weapon_course_deg": fire.weapon_course_deg,
            "feasible": fire.feasible,
            "closest_approach_m": fire.closest_approach_m,
        }

        # Step 6 — acoustic link: link budget over the wreck uplink.
        link_budget = sc.link_budget
        results["acoustic_link"] = {
            "range_m": ATAC_LINK_RANGE_M,
            "received_snr_db": link_budget.received_snr_db,
            "transmission_loss_db": link_budget.transmission_loss_db,
            "closes": link_budget.closes,
            "max_range_m": link_budget.max_range_m,
        }

        input_hash = _input_hash(
            MISSION_SEED,
            escrow.key_fingerprint,
            sc.released_key,
            fire.intercept_time_s,
            link_budget.received_snr_db,
            route.path,
        )
        return MissionOutcome(
            # Derived from the computed scenario, never stapled — see
            # `mission_succeeded`. The preflight verdict of the same name is
            # only meaningful because this value can be False.
            success=mission_succeeded(sc),
            results=results,
            provenance=Provenance(
                package_version=_PACKAGE_VERSION,
                seed=MISSION_SEED,
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
