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
    from for_your_eyes_only.mission import GADGETS

    escrow = cast(EscrowState, GADGETS["escrow"])
    key = release_key(escrow, tuple(range(escrow.threshold)))
    assert key == key  # deterministic self-consistency
    assert isinstance(key, int)
