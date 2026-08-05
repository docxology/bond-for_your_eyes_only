"""Error and edge paths across the ATAC domain modules.

Each guard in the codebase is either reachable and worth binding, or it is dead
code that should be deleted. These tests take the first position: every check
here is driven through real inputs and real computation, so a guard that stops
protecting anything shows up as a failing test rather than as quietly
unexercised lines.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from for_your_eyes_only import island_routing as ir
from for_your_eyes_only import key_escrow as ke
from for_your_eyes_only import key_recovery as kr
from for_your_eyes_only import manuscript_variables as mv
from for_your_eyes_only import targeting as tg
from for_your_eyes_only import underwater_retrieval as uw

# --------------------------------------------------------------------------- #
# island_routing
# --------------------------------------------------------------------------- #


def _disconnected_graph() -> ir.IslandGraph:
    """Two islands with no edge between their components."""
    return ir.IslandGraph(
        nodes={"alpha": (0.0, 0.0), "beta": (1.0, 1.0), "island": (50.0, 50.0)},
        adjacency={
            "alpha": (ir.Edge("beta", 2.0, 0.1),),
            "beta": (ir.Edge("alpha", 2.0, 0.1),),
            "island": (),
        },
    )


def test_plan_route_raises_when_no_route_exists() -> None:
    graph = _disconnected_graph()
    with pytest.raises(ValueError, match="no route"):
        ir.plan_route(graph, "alpha", "island")


def test_plan_route_raises_on_unknown_node() -> None:
    graph = ir.build_ionian_graph()
    with pytest.raises(KeyError):
        ir.plan_route(graph, "corfu", "atlantis")


def test_plan_route_revisits_are_skipped_not_reprocessed() -> None:
    """A node reachable by two costs is settled once, at the cheaper cost.

    The diamond below pushes `d` onto the frontier twice; the second pop must be
    discarded rather than overwrite the settled result.
    """
    graph = ir.IslandGraph(
        nodes={"a": (0.0, 0.0), "b": (1.0, 0.0), "c": (0.0, 1.0), "d": (1.0, 1.0)},
        adjacency={
            "a": (ir.Edge("b", 1.0, 0.0), ir.Edge("c", 1.0, 0.0)),
            "b": (ir.Edge("a", 1.0, 0.0), ir.Edge("d", 5.0, 0.0)),
            "c": (ir.Edge("a", 1.0, 0.0), ir.Edge("d", 1.0, 0.0)),
            "d": (ir.Edge("b", 5.0, 0.0), ir.Edge("c", 1.0, 0.0)),
        },
    )
    plan = ir.plan_route(graph, "a", "d", risk_weight=0.0, use_astar=False)
    assert plan.path == ("a", "c", "d")
    assert plan.total_cost == pytest.approx(2.0)


def test_stale_frontier_entry_is_discarded_on_pop() -> None:
    """A node re-pushed at a lower cost leaves a stale entry that must be skipped.

    ``b`` is first reached at cost 10, then improved to 2 via ``c``. The stale
    ``b @ 10`` stays on the heap and is popped later; settling it a second time
    would corrupt the predecessor chain.
    """
    graph = ir.IslandGraph(
        nodes={"a": (0.0, 0.0), "b": (1.0, 0.0), "c": (0.0, 1.0), "d": (2.0, 2.0)},
        adjacency={
            "a": (ir.Edge("b", 10.0, 0.0), ir.Edge("c", 1.0, 0.0)),
            "b": (ir.Edge("a", 10.0, 0.0), ir.Edge("c", 1.0, 0.0), ir.Edge("d", 100.0, 0.0)),
            "c": (ir.Edge("a", 1.0, 0.0), ir.Edge("b", 1.0, 0.0)),
            "d": (ir.Edge("b", 100.0, 0.0),),
        },
    )
    plan = ir.plan_route(graph, "a", "d", risk_weight=0.0, use_astar=False)
    # The improved route through c wins; b is settled once, at cost 2.
    assert plan.path == ("a", "c", "b", "d")
    assert plan.total_cost == pytest.approx(102.0)


def test_edge_distance_rejects_non_adjacent_nodes() -> None:
    """A non-adjacent pair is an error, not a silent straight-line guess."""
    graph = ir.build_ionian_graph()
    assert ir.edge_distance(graph, "corfu", "paxi") == pytest.approx(9.0)
    with pytest.raises(KeyError, match="no edge"):
        ir.edge_distance(graph, "corfu", "zakynthos")


def test_dijkstra_and_astar_agree() -> None:
    """A* with an admissible heuristic returns the same optimum as Dijkstra."""
    graph = ir.build_ionian_graph()
    a = ir.plan_route(graph, "corfu", "wreck_site", use_astar=True)
    b = ir.plan_route(graph, "corfu", "wreck_site", use_astar=False)
    assert a.path == b.path
    assert a.total_cost == pytest.approx(b.total_cost)


# --------------------------------------------------------------------------- #
# key_escrow
# --------------------------------------------------------------------------- #


def test_escrow_state_rejects_single_custodian_quorum() -> None:
    with pytest.raises(ValueError, match="threshold must be >= 2"):
        ke.EscrowState(
            key_fingerprint="f",
            threshold=1,
            num_shares=2,
            prime=ke.PRIME,
            shares=((1, 2), (3, 4)),
            commitments=(5, 6),
            custodian_labels=("a", "b"),
        )


def test_escrow_state_rejects_share_count_mismatch() -> None:
    with pytest.raises(ValueError, match="inconsistent with shares"):
        ke.EscrowState(
            key_fingerprint="f",
            threshold=2,
            num_shares=5,
            prime=ke.PRIME,
            shares=((1, 2), (3, 4)),
            commitments=(5, 6),
            custodian_labels=("a", "b"),
        )


def test_escrow_state_rejects_undercovering_commitments() -> None:
    with pytest.raises(ValueError, match="commitments must cover"):
        ke.EscrowState(
            key_fingerprint="f",
            threshold=2,
            num_shares=2,
            prime=ke.PRIME,
            shares=((1, 2), (3, 4)),
            commitments=(5,),
            custodian_labels=("a", "b"),
        )


def test_mod_inverse_rejects_non_invertible_element() -> None:
    """2 has no inverse mod 4 — the extended-Euclid gcd guard must fire."""
    with pytest.raises(ke.EscrowError, match="not invertible"):
        ke.mod_inverse(2, 4)


def test_create_escrow_rejects_custodian_count_mismatch() -> None:
    with pytest.raises(ke.EscrowError, match="custodian labels"):
        ke.create_escrow(1234, threshold=2, num_shares=3, custodian_labels=("only", "two"))


def test_release_rejects_out_of_range_share_index() -> None:
    escrow = ke.create_escrow(1234, threshold=2, num_shares=3, custodian_labels=("a", "b", "c"), seed=3)
    with pytest.raises(ke.EscrowError, match="out of range"):
        ke.release_key(escrow, (0, 99))


def test_key_bound_keeps_keys_inside_the_field() -> None:
    assert ke.KEY_BOUND < ke.PRIME


def test_split_key_rejects_duplicate_evaluation_points() -> None:
    """Shares must sit at distinct x; a repeated draw is resampled, not accepted.

    Over the 61-bit production field a collision never happens, so the rejection
    loop is exercised here over a deliberately tiny field where it must.
    """
    shares = ke.split_key(3, threshold=2, num_shares=5, prime=7, seed=0)
    xs = [x for x, _y in shares]
    assert len(xs) == 5
    assert len(set(xs)) == 5, "split_key emitted duplicate evaluation points"
    assert all(1 <= x < 7 for x in xs)


# --------------------------------------------------------------------------- #
# key_recovery
# --------------------------------------------------------------------------- #


def test_vandermonde_solve_rejects_singular_system() -> None:
    """Linearly dependent rows cannot recover a key and must say so."""
    prime = ke.PRIME
    rows = [(1, 1), (1, 1)]  # duplicate rows -> singular
    with pytest.raises(ValueError, match="singular"):
        kr._vandermonde_solve(rows, [5, 5], 2, prime)  # noqa: SLF001 - guard under test


def test_vandermonde_solve_skips_already_eliminated_rows() -> None:
    """A row whose pivot column is already zero needs no elimination step."""
    prime = ke.PRIME
    # Identity system: row 1 already has 0 in the pivot column.
    solved = kr._vandermonde_solve([(1, 0), (0, 1)], [7, 9], 2, prime)  # noqa: SLF001
    assert solved == (7, 9)


def test_erasure_code_points_are_distinct_field_elements() -> None:
    code = kr.ErasureCode(data_symbols=3, code_symbols=5)
    points = code.points()
    assert points == (1, 2, 3, 4, 5)
    assert len(set(points)) == len(points)


# --------------------------------------------------------------------------- #
# targeting
# --------------------------------------------------------------------------- #


def test_angle_between_degenerate_vectors_is_zero() -> None:
    """A zero-length vector has no direction; the guard returns 0 rather than NaN."""
    assert tg._angle_between((0.0, 0.0), (1.0, 0.0)) == 0.0  # noqa: SLF001 - guard under test
    assert tg._angle_between((1.0, 0.0), (0.0, 0.0)) == 0.0  # noqa: SLF001 - guard under test


def test_intercept_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="target_range_m"):
        tg.intercept_solution(-1.0, 0.0, 0.0, 1.0, 2.0)
    with pytest.raises(ValueError, match="speeds"):
        tg.intercept_solution(100.0, 0.0, 0.0, 1.0, 0.0)


def test_equal_speed_crossing_target_has_no_intercept() -> None:
    """Equal speeds degenerate the quadratic to a linear equation with no root.

    A target crossing exactly abeam gives ``p0 . v_t == 0``, so the linear term
    vanishes and the weapon can never close: the constant-bearing solution does
    not exist even though both platforms are equally fast.
    """
    solution = tg.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,  # target due north
        target_course_deg=90.0,  # running due east, exactly abeam
        target_speed_ms=20.0,
        weapon_speed_ms=20.0,  # equal speeds -> quadratic term vanishes
    )
    assert solution.feasible is False
    assert math.isinf(solution.intercept_time_s)
    assert math.isfinite(solution.closest_approach_m)


def test_faster_crossing_target_gives_negative_discriminant() -> None:
    """A faster target crossing abeam makes the quadratic have no real root."""
    solution = tg.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,
        target_course_deg=90.0,
        target_speed_ms=50.0,  # faster than the weapon
        weapon_speed_ms=5.0,
    )
    assert solution.feasible is False
    assert math.isinf(solution.intercept_time_s)
    assert solution.closest_approach_m > 0.0


def test_infeasible_intercept_reports_finite_closest_approach() -> None:
    """A target faster than the weapon cannot be caught; the fallback still lands."""
    solution = tg.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,
        target_course_deg=0.0,
        target_speed_ms=50.0,
        weapon_speed_ms=5.0,
    )
    assert solution.feasible is False
    assert math.isinf(solution.intercept_time_s)
    assert math.isfinite(solution.closest_approach_m)
    assert solution.closest_approach_m > 0.0


# --------------------------------------------------------------------------- #
# underwater_retrieval
# --------------------------------------------------------------------------- #


def test_haldane_rejects_m_value_at_or_below_surface_pressure() -> None:
    with pytest.raises(ValueError, match="exceed 1.0"):
        uw.HaldaneModel(half_times=(34.0,), m_values=(1.0,))


def test_format_schedule_keeps_bottom_depth_when_bottom_time_is_zero() -> None:
    """A zero bottom time must not report the bottom as being at the surface."""
    profile = uw.plan_descent(30.0, bottom_time_s=0.0)
    schedule = uw.format_schedule(profile)
    bottom = [row for row in schedule.rows if row[0] == "bottom"]
    assert len(bottom) == 1
    assert bottom[0][1] == pytest.approx(30.0)
    assert bottom[0][2] == pytest.approx(0.0)


def test_plan_descent_validates_inputs() -> None:
    with pytest.raises(ValueError, match="depth_m"):
        uw.plan_descent(0.0)
    with pytest.raises(ValueError, match="descent_rate"):
        uw.plan_descent(10.0, descent_rate=0.0)
    with pytest.raises(ValueError, match="bottom_time_s"):
        uw.plan_descent(10.0, bottom_time_s=-1.0)


def test_retrieval_planner_rejects_non_positive_depth() -> None:
    with pytest.raises(ValueError, match="wreck_depth"):
        uw.RetrievalPlanner(wreck_depth=0.0)


# --------------------------------------------------------------------------- #
# manuscript_variables
# --------------------------------------------------------------------------- #


def test_config_must_be_a_mapping(tmp_path: Path) -> None:
    bad = tmp_path / "config.yaml"
    bad.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level mapping"):
        mv.load_manuscript_config(bad)


def test_paper_section_must_be_a_mapping(tmp_path: Path) -> None:
    bad = tmp_path / "config.yaml"
    bad.write_text("paper: just-a-string\n", encoding="utf-8")
    with pytest.raises(ValueError, match="'paper' section"):
        mv.generate_variables(config_path=bad)


def _failing_metrics() -> dict[str, str]:
    """A real provider that fails, standing in for a broken domain module."""
    raise RuntimeError("domain module unavailable")


def test_strict_mode_raises_when_metrics_cannot_be_computed() -> None:
    with pytest.raises(ValueError, match="failed to produce live outputs"):
        mv.generate_variables(require_outputs=True, metrics_provider=_failing_metrics)


def test_draft_mode_falls_back_to_na_for_every_metric_token() -> None:
    """Draft mode degrades to N/A — and covers the whole live metric set."""
    variables = mv.generate_variables(require_outputs=False, metrics_provider=_failing_metrics)
    assert mv.METRIC_TOKENS, "metric token set must not be empty"
    for token in mv.METRIC_TOKENS:
        assert variables[token] == "N/A", f"{token} did not fall back to N/A"
    # Non-metric tokens are still populated from config.
    assert variables["BOND_CODENAME"] == "ATAC"


def test_metric_tokens_match_the_live_metric_set() -> None:
    """METRIC_TOKENS is derived, so it cannot drift from the real metric map."""
    live = mv.generate_variables(require_outputs=True)
    for token in mv.METRIC_TOKENS:
        assert token in live
        assert live[token] != "N/A"
