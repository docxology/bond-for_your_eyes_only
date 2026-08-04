"""Real-data tests for the underwater retrieval planning module."""

import math

import pytest

from for_your_eyes_only import underwater_retrieval as uw


def test_plan_descent_creates_profile():
    """A default descent produces descent, bottom, ascent stages summing to total."""
    profile = uw.plan_descent(42.0, bottom_time_s=600.0)
    assert profile.max_depth() == pytest.approx(42.0)
    assert profile.bottom_time_s == 600.0
    assert len(profile.descent_stages) == 1
    assert len(profile.ascent_stages) >= 1
    expected_ascent = sum(s.duration_s for s in profile.ascent_stages)
    expected_total = 42.0 / uw.DESCENT_RATE + 600.0 + expected_ascent
    assert profile.total_time_s == pytest.approx(expected_total)


def test_plan_descent_deterministic():
    a = uw.plan_descent(42.0, bottom_time_s=600.0)
    b = uw.plan_descent(42.0, bottom_time_s=600.0)
    assert a == b


def test_plan_descent_validation():
    with pytest.raises(ValueError):
        uw.plan_descent(0.0)
    with pytest.raises(ValueError):
        uw.plan_descent(-5.0)
    with pytest.raises(ValueError):
        uw.plan_descent(42.0, descent_rate=0.0)
    with pytest.raises(ValueError):
        uw.plan_descent(42.0, bottom_time_s=-1.0)


def test_current_offset_proportional_to_time():
    """Offset = current * time (drift grows linearly with dive time)."""
    offset = uw.current_offset((-0.12, 0.05), 100.0)
    assert offset == pytest.approx((-12.0, 5.0))
    offset2 = uw.current_offset((-0.12, 0.05), 200.0)
    assert offset2 == pytest.approx((-24.0, 10.0))


def test_zero_current_zero_offset():
    assert uw.current_offset((0.0, 0.0), 123.0) == (0.0, 0.0)


def test_tissue_saturation_limits():
    """Saturation tends to ambient for long exposure; stays at initial for zero time."""
    model = uw.HaldaneModel()
    initial, ambient = 1.0, 42.0
    s0 = uw.tissue_saturation(initial, ambient, 0.0, model.half_times[0])
    assert s0 == pytest.approx(initial)
    s_long = uw.tissue_saturation(initial, ambient, 1e6, model.half_times[0])
    assert s_long == pytest.approx(ambient, rel=1e-3)
    assert initial < s_long


def test_no_decompression_limit_shallow_vs_deep():
    """Deeper target -> shorter (or zero) no-decompression bottom time."""
    model = uw.HaldaneModel()
    shallow = uw.no_decompression_limit(model, 10.0)
    deep = uw.no_decompression_limit(model, 60.0)
    # shallow gives finite positive bottom time; deep gives <= that
    assert shallow > 0
    assert deep <= shallow
    # zero depth -> infinite (no limit at the surface)
    assert uw.no_decompression_limit(model, 0.0) == math.inf


def test_haldane_model_validation():
    with pytest.raises(ValueError):
        uw.HaldaneModel(half_times=(1.0,), m_values=(1.0, 2.0))
    with pytest.raises(ValueError):
        uw.HaldaneModel(half_times=(0.0,), m_values=(1.0,))


def test_haldane_model_tau():
    model = uw.HaldaneModel(half_times=(34.0,), m_values=(2.72,))
    assert model.tau(0) == pytest.approx(34.0 / math.log(2.0))
    assert model.compartments() == 1
    assert model.ceiling_m(0, 40.0) == pytest.approx(2.72 * 40.0)


def test_retrieval_planner_plan():
    planner = uw.RetrievalPlanner(wreck_depth=42.0)
    plan = planner.plan()
    assert plan.total_time_s > 0
    assert plan.current == uw.DEFAULT_CURRENT
    assert len(plan.surface_offset) == 2
    assert isinstance(plan.target_reachable, bool)
    # default offset should be within the 200 m envelope for a 42 m dive
    assert plan.target_reachable is True


def test_retrieval_planner_unreachable():
    """A large current / long time throws the offset outside the envelope."""
    planner = uw.RetrievalPlanner(wreck_depth=42.0, current=(10.0, 0.0), bottom_time_s=3600.0, max_offset_m=10.0)
    plan = planner.plan()
    assert plan.target_reachable is False


def test_retrieval_planner_deterministic():
    a = uw.RetrievalPlanner().plan()
    b = uw.RetrievalPlanner().plan()
    assert a == b


def test_retrieval_planner_validation():
    with pytest.raises(ValueError):
        uw.RetrievalPlanner(wreck_depth=0.0)


def test_format_schedule_rows():
    profile = uw.plan_descent(42.0, bottom_time_s=600.0)
    schedule = uw.format_schedule(profile)
    assert schedule.rows[0][0] == "descent"
    phases = [r[0] for r in schedule.rows]
    assert "descent" in phases and "bottom" in phases and "ascent" in phases
