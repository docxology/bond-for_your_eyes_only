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

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from for_your_eyes_only import manuscript_variables as mv
from for_your_eyes_only import mission

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PACKAGE_ROOT / "manuscript" / "config.yaml"


def _check_escrow_block(declared: dict[str, Any]) -> None:
    """The escrow half of the pin, factored out so the positive control can run it.

    The control must drive *this* function — the same comparison production
    verification depends on — over a mutated config actually loaded from disk.
    Re-stating the comparison inside the control would prove nothing about it.
    """
    escrow = declared["escrow"]
    assert escrow["threshold"] == mission.ESCROW_THRESHOLD
    assert escrow["num_shares"] == mission.ESCROW_SHARES
    assert tuple(escrow["custodians"]) == mission.CUSTODIANS
    assert escrow["seed"] == mission.MISSION_SEED


@pytest.fixture(scope="module")
def declared() -> dict[str, Any]:
    """The ``mission:`` block declared in manuscript/config.yaml."""
    config = mv.load_manuscript_config(CONFIG_PATH)
    block = config["mission"]
    assert isinstance(block, dict) and block, "config.yaml must declare a non-empty mission block"
    return block


def test_identity_matches(declared: dict[str, Any]) -> None:
    assert declared["codename"] == mission.ATAC_MISSION
    assert declared["slug"] == mission.SLUG


def test_escrow_block_matches_mission_constants(declared: dict[str, Any]) -> None:
    _check_escrow_block(declared)


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
    from for_your_eyes_only import acoustic_link as ac

    acoustic = declared["acoustic"]
    assert acoustic["frequency_khz"] == pytest.approx(mission.ATAC_LINK.frequency_khz)
    assert acoustic["range_m"] == pytest.approx(mission.ATAC_LINK_RANGE_M)
    assert acoustic["detection_threshold_db"] == pytest.approx(mission.ATAC_LINK.detection_threshold_db)
    assert acoustic["sea_state"] == pytest.approx(mission.ATAC_SEA_STATE)
    assert acoustic["spreading"] == pytest.approx(mission.ATAC_LINK.spreading)
    # The declared sea state is the one the noise term is actually computed
    # from — not a decorative number sitting beside a hand-typed dB literal.
    assert mission.ATAC_LINK.noise_level_db == pytest.approx(ac.noise_level(acoustic["sea_state"]))


def test_underwater_block_matches_planner_defaults(declared: dict[str, Any]) -> None:
    from for_your_eyes_only import underwater_retrieval as uw

    underwater = declared["underwater"]
    planner = uw.RetrievalPlanner()
    assert underwater["wreck_depth"] == pytest.approx(uw.DEFAULT_WRECK_DEPTH)
    assert underwater["bottom_time_s"] == pytest.approx(planner.bottom_time_s)
    assert underwater["max_offset_m"] == pytest.approx(planner.max_offset_m)


def test_the_pin_can_actually_fail(tmp_path: Path) -> None:
    """Positive control: a mutated config, loaded from disk, must fail the pin.

    The previous version of this control built ``dict(declared['escrow'],
    threshold=THRESHOLD + 1)`` and asserted ``X + 1 != X``. That is true of any
    integer and never touched the load-and-compare mechanism at all: every
    assertion in this file could have been self-comparing and it would still
    have been green. This version writes a real config file with one wrong
    value, loads it through the production loader, and requires the production
    check to raise.
    """
    config = mv.load_manuscript_config(CONFIG_PATH)
    mutated = copy.deepcopy(config)
    mutated["mission"]["escrow"]["threshold"] = mission.ESCROW_THRESHOLD + 1
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")

    reloaded = mv.load_manuscript_config(path)["mission"]
    with pytest.raises(AssertionError):
        _check_escrow_block(reloaded)

    # ...and the same loader over an unmutated round-trip still passes, so the
    # failure above is attributable to the wrong value, not to the round-trip.
    clean = tmp_path / "clean.yaml"
    clean.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    _check_escrow_block(mv.load_manuscript_config(clean)["mission"])
