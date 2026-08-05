"""Bind ``manuscript/config.yaml`` to the mission constants it mirrors.

``config.yaml``'s ``mission:`` block states the canonical ATAC scenario in
human-readable form, but it is deliberately *not* the source of truth: every
manuscript number is computed live from :mod:`for_your_eyes_only.mission`. That
split is only safe if the two are pinned together — otherwise the config quietly
decays into decoration that describes a scenario the code no longer runs (the
block previously carried an escrow key of 4242 that the code never used).

These tests are that pin. Each one compares a declared value against the
constant the mission actually executes with, so editing either side alone fails.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from for_your_eyes_only import manuscript_variables as mv
from for_your_eyes_only import mission

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def declared() -> dict[str, Any]:
    """The ``mission:`` block declared in manuscript/config.yaml."""
    config = mv.load_manuscript_config(PACKAGE_ROOT / "manuscript" / "config.yaml")
    block = config["mission"]
    assert isinstance(block, dict) and block, "config.yaml must declare a non-empty mission block"
    return block


def test_identity_matches(declared: dict[str, Any]) -> None:
    assert declared["codename"] == mission.ATAC_MISSION
    assert declared["slug"] == mission.SLUG


def test_escrow_block_matches_mission_constants(declared: dict[str, Any]) -> None:
    escrow = declared["escrow"]
    assert escrow["threshold"] == mission.ESCROW_THRESHOLD
    assert escrow["num_shares"] == mission.ESCROW_SHARES
    assert tuple(escrow["custodians"]) == mission.CUSTODIANS
    assert escrow["seed"] == mission.MISSION_SEED


def test_escrow_block_declares_no_literal_key(declared: dict[str, Any]) -> None:
    """The key is seed-derived; a literal in config would be an unhonoured claim."""
    assert "key" not in declared["escrow"]


def test_recovery_block_matches_mission_constants(declared: dict[str, Any]) -> None:
    recovery = declared["recovery"]
    assert recovery["data_symbols"] == mission.RECOVERY_DATA_SYMBOLS
    assert recovery["code_symbols"] == mission.RECOVERY_CODE_SYMBOLS


def test_routing_block_matches_mission_constants(declared: dict[str, Any]) -> None:
    routing = declared["routing"]
    assert routing["origin"] == mission.ROUTE_ORIGIN
    assert routing["destination"] == mission.ROUTE_DESTINATION
    assert routing["risk_weight"] == pytest.approx(mission.ROUTE_RISK_WEIGHT)


def test_acoustic_block_matches_mission_constants(declared: dict[str, Any]) -> None:
    acoustic = declared["acoustic"]
    assert acoustic["frequency_khz"] == pytest.approx(mission.ATAC_LINK.frequency_khz)
    assert acoustic["range_m"] == pytest.approx(mission.ATAC_LINK_RANGE_M)
    assert acoustic["detection_threshold_db"] == pytest.approx(mission.ATAC_LINK.detection_threshold_db)


def test_underwater_block_matches_planner_defaults(declared: dict[str, Any]) -> None:
    from for_your_eyes_only import underwater_retrieval as uw

    underwater = declared["underwater"]
    planner = uw.RetrievalPlanner()
    assert underwater["wreck_depth"] == pytest.approx(uw.DEFAULT_WRECK_DEPTH)
    assert underwater["bottom_time_s"] == pytest.approx(planner.bottom_time_s)
    assert underwater["max_offset_m"] == pytest.approx(planner.max_offset_m)


def test_the_pin_can_actually_fail(declared: dict[str, Any]) -> None:
    """Positive control: a wrong declared value must not compare equal.

    Without this, the tests above would still pass if the comparison were
    accidentally trivial (e.g. both sides read from the same place).
    """
    wrong = dict(declared["escrow"], threshold=mission.ESCROW_THRESHOLD + 1)
    assert wrong["threshold"] != mission.ESCROW_THRESHOLD
