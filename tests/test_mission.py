"""Tests for the mission adapter: protocol conformance, gadgets, full flow."""

from bond_api import GadgetRegistry, MissionProvider as ProtocolProvider
from bond_api.protocol import ReconRequest, run_mission

from for_your_eyes_only import mission
from for_your_eyes_only.mission import MissionProvider


def test_provider_satisfies_protocol():
    """The provider is a valid runtime-checkable MissionProvider."""
    provider = MissionProvider()
    assert isinstance(provider, ProtocolProvider)
    assert provider.film == "for_your_eyes_only"


def test_brief_declares_mission():
    provider = MissionProvider()
    brief = provider.brief()
    assert brief.film == "for_your_eyes_only"
    assert brief.codename == "ATAC"
    assert len(brief.objectives) >= 2
    assert len(brief.assets) == 1
    assert brief.assets[0].kind == "escrow"
    assert len(brief.constraints) == 2


def test_recon_returns_findings():
    provider = MissionProvider()
    report = provider.recon(ReconRequest(goal="recover the lost ATAC device"))
    assert len(report.findings) >= 3
    labels = {f.label for f in report.findings}
    assert {"goal", "escrow", "constraints"} <= labels


def test_plan_sequences_concepts():
    provider = MissionProvider()
    plan = provider.plan(provider.brief())
    actions = [s.action for s in plan.steps]
    assert actions == [
        "release_key",
        "recover_erasure",
        "retrieval_planner.plan",
        "plan_route",
        "intercept_solution",
        "compute_link_budget",
    ]


def test_execute_produces_deterministic_results():
    provider = MissionProvider()
    outcome = provider.execute(provider.plan(provider.brief()))
    assert outcome.success is True
    assert set(outcome.results.keys()) == {
        "escrow_release",
        "key_recovery",
        "underwater_retrieval",
        "island_routing",
        "targeting",
        "acoustic_link",
    }
    assert outcome.results["escrow_release"]["fingerprint_match"] is True
    assert outcome.results["key_recovery"]["matches"] is True
    assert len(outcome.results["island_routing"]["path"]) >= 2
    assert outcome.results["underwater_retrieval"]["target_reachable"] is True
    assert outcome.results["targeting"]["feasible"] is True
    assert outcome.results["acoustic_link"]["closes"] is True
    # determinism: identical input hash
    again = provider.execute(provider.plan(provider.brief()))
    assert outcome.provenance.input_hash == again.provenance.input_hash
    assert outcome.provenance.seed == 7
    assert outcome.provenance.wall_time_s == 0.0


def test_plan_states_the_erasure_geometry_the_right_way_round():
    """The `key_recovery` step's code label is k-of-n, derived from constants.

    It was the hardcoded string "6-of-4" — the geometry backwards (six required
    of four stored) — printed verbatim by `scripts/plan.py` with no gate on it.
    """
    provider = MissionProvider()
    step = next(s for s in provider.plan(provider.brief()).steps if s.name == "key_recovery")
    data, _, code = str(step.params["code"]).partition("-of-")
    assert int(data) == mission.RECOVERY_DATA_SYMBOLS
    assert int(code) == mission.RECOVERY_CODE_SYMBOLS
    # k of n, not n of k: fewer symbols are required than are stored.
    assert int(data) < int(code)
    assert step.params["code"] == "4-of-6"


def test_mission_success_is_derived_and_can_be_false():
    """Positive control for the `mission_success` preflight verdict.

    `execute()` used to return `MissionOutcome(success=True, ...)` as a literal,
    so `scripts/00_preflight.py`'s `[PASS] mission_success` could not fail for
    any input. `success` is now `mission_succeeded(scenario)`; here the real
    canonical scenario is degraded — one field at a time, through
    `dataclasses.replace` on the real frozen dataclass — and each degradation
    must flip the verdict to False.
    """
    import dataclasses

    from for_your_eyes_only.mission import canonical_mission, mission_succeeded

    good = canonical_mission()
    assert mission_succeeded(good) is True

    degradations = [
        dataclasses.replace(good, fingerprint_match=False),
        dataclasses.replace(good, recovery_recovered=tuple(v + 1 for v in good.recovery_recovered)),
        dataclasses.replace(good, retrieval=dataclasses.replace(good.retrieval, target_reachable=False)),
        dataclasses.replace(good, route=dataclasses.replace(good.route, path=("corfu", "paxi"))),
        dataclasses.replace(good, fire=dataclasses.replace(good.fire, feasible=False)),
        dataclasses.replace(good, link_budget=dataclasses.replace(good.link_budget, closes=False)),
    ]
    for i, degraded in enumerate(degradations):
        assert mission_succeeded(degraded) is False, f"degradation {i} did not flip the verdict"


def test_debrief_carries_lessons():
    provider = MissionProvider()
    debrief = provider.debrief(provider.execute(provider.plan(provider.brief())))
    assert debrief.outcome.success is True
    assert len(debrief.lessons) == 3


def test_run_mission_full_flow():
    provider = MissionProvider()
    debrief = run_mission(provider, ReconRequest(goal="recover the lost ATAC device"))
    assert debrief.outcome.success is True
    assert debrief.outcome.results["island_routing"]["path"][-1] == "wreck_site"


def test_gadgets_registered():
    """GADGETS registers escrow + domain builders."""
    from for_your_eyes_only.mission import GADGETS

    registry = GadgetRegistry()
    registry.register("for_your_eyes_only", GADGETS)
    assert registry.contains("for_your_eyes_only", "escrow")
    assert registry.contains("for_your_eyes_only", "release_key")
    assert registry.contains("for_your_eyes_only", "plan_route")
    assert registry.contains("for_your_eyes_only", "build_ionian_graph")
    assert set(registry.gadgets_for("for_your_eyes_only")) == set(GADGETS.keys())


def test_build_gadgets_is_deterministic():
    a = mission.build_gadgets()
    b = mission.build_gadgets()
    assert a["escrow"] == b["escrow"]


def test_releasing_gadget_escrow_recovers():
    from typing import cast

    from for_your_eyes_only.key_escrow import EscrowState, release_key
    from for_your_eyes_only.mission import GADGETS, key_fingerprint

    escrow = cast(EscrowState, GADGETS["escrow"])
    key = release_key(escrow, tuple(range(escrow.threshold)))
    assert isinstance(key, int)
    # Bind the released key to something outside itself. `assert key == key`
    # (the earlier assertion here) is a value compared to itself and cannot
    # fail; these can. The key must re-derive the escrow's stored fingerprint,
    # a *different* quorum must return the same key, and it must land in the
    # field the escrow was built over.
    assert key_fingerprint(key) == escrow.key_fingerprint
    assert release_key(escrow, (escrow.num_shares - 1, escrow.num_shares - 2)) == key
    assert 0 < key < escrow.prime
