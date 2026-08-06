"""Real-data tests for the ATAC fire-control targeting module."""

import math

import pytest

from for_your_eyes_only import targeting


def test_normalise_course():
    assert targeting.normalise_course(0.0) == 0.0
    assert targeting.normalise_course(360.0) == 0.0
    assert targeting.normalise_course(450.0) == 90.0
    assert targeting.normalise_course(-30.0) == 330.0


def test_polar_to_velocity_north():
    east, north = targeting.polar_to_velocity(10.0, 0.0)
    assert east == pytest.approx(0.0)
    assert north == pytest.approx(10.0)


def test_polar_to_velocity_east():
    east, north = targeting.polar_to_velocity(10.0, 90.0)
    assert east == pytest.approx(10.0)
    assert north == pytest.approx(0.0)


def test_feasible_head_on_intercept():
    """A target closing straight at the launcher is intercepted in the expected time."""
    # Target at 4000 m due south-ish closing at 8 m/s; weapon at 45 m/s.
    solution = targeting.intercept_solution(
        target_range_m=4000.0,
        target_bearing_deg=0.0,  # due north
        target_course_deg=180.0,  # heading south (toward launcher)
        target_speed_ms=8.0,
        weapon_speed_ms=45.0,
    )
    assert solution.feasible is True
    assert solution.intercept_time_s > 0
    # closing speed = 45 + 8 = 53 m/s -> t = 4000/53 ≈ 75.5 s
    assert solution.intercept_time_s == pytest.approx(4000.0 / 53.0, rel=1e-3)
    assert solution.lead_angle_deg == pytest.approx(0.0, abs=1e-3)


def test_feasible_stationary_target():
    """A stationary target gives a weapon-course directly along the line of sight."""
    solution = targeting.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=45.0,
        target_course_deg=0.0,
        target_speed_ms=0.0,
        weapon_speed_ms=50.0,
    )
    assert solution.feasible is True
    assert solution.intercept_time_s == pytest.approx(20.0, rel=1e-3)
    assert solution.lead_angle_deg == pytest.approx(0.0, abs=1e-3)
    assert solution.weapon_course_deg == pytest.approx(45.0, abs=1e-3)


def test_equal_speed_closing_intercept():
    """Weapon == target speed, closing head-on: linear branch, meet halfway."""
    solution = targeting.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,
        target_course_deg=180.0,  # closing
        target_speed_ms=10.0,
        weapon_speed_ms=10.0,
    )
    assert solution.feasible is True
    assert solution.intercept_time_s == pytest.approx(50.0, rel=1e-3)


def test_equal_speed_receding_infeasible():
    """Weapon == target speed, target receding: no positive linear root."""
    solution = targeting.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,
        target_course_deg=0.0,  # receding away
        target_speed_ms=10.0,
        weapon_speed_ms=10.0,
    )
    assert solution.feasible is False
    assert solution.intercept_time_s == math.inf


def test_infeasible_target_outruns():
    """A much faster target flying away is not interceptable -> closest approach."""
    solution = targeting.intercept_solution(
        target_range_m=1000.0,
        target_bearing_deg=0.0,
        target_course_deg=0.0,  # heading away, same dir as LOS
        target_speed_ms=100.0,
        weapon_speed_ms=30.0,
    )
    assert solution.feasible is False
    assert solution.intercept_time_s == math.inf
    assert solution.closest_approach_m >= 0.0
    # target pulls away -> closest approach is the initial range (or beyond)
    assert solution.closest_approach_m >= 1000.0


def test_lead_angle_positive_for_crossing_target():
    """A crossing target needs a non-trivial lead angle."""
    solution = targeting.intercept_solution(
        target_range_m=5000.0,
        target_bearing_deg=45.0,
        target_course_deg=120.0,
        target_speed_ms=8.0,
        weapon_speed_ms=45.0,
    )
    assert solution.feasible is True
    assert solution.lead_angle_deg > 0.0
    assert 0.0 < solution.weapon_course_deg < 90.0


def test_canonical_scenario_matches_mission():
    """The canonical ATAC scenario used by the mission is feasible with a lead."""
    from for_your_eyes_only.mission import canonical_mission

    fire = canonical_mission().fire
    assert fire.feasible is True
    assert fire.lead_angle_deg > 0.0
    assert fire.closest_approach_m > 0.0


def test_determinism():
    a = targeting.intercept_solution(4000.0, 45.0, 120.0, 8.0, 45.0)
    b = targeting.intercept_solution(4000.0, 45.0, 120.0, 8.0, 45.0)
    assert a == b


def test_validation():
    with pytest.raises(ValueError):
        targeting.intercept_solution(-1.0, 0.0, 0.0, 0.0, 10.0)
    with pytest.raises(ValueError):
        targeting.intercept_solution(100.0, 0.0, 0.0, -5.0, 10.0)
    with pytest.raises(ValueError):
        targeting.intercept_solution(100.0, 0.0, 0.0, 0.0, 0.0)


def test_closest_approach_parallel_equal_speed():
    """Parallel, equal-speed relative motion keeps range constant."""
    ca, t = targeting.closest_approach((100.0, 0.0), (5.0, 0.0), (5.0, 0.0))
    assert ca == pytest.approx(100.0)
    assert t == 0.0


def test_closest_approach_direct_collision():
    """Relative motion straight at each other -> closest approach 0."""
    ca, t = targeting.closest_approach((100.0, 0.0), (-10.0, 0.0), (0.0, 0.0))
    assert ca == pytest.approx(0.0, abs=1e-6)
    assert t == pytest.approx(10.0)


def test_stationary_zero_vector_angle():
    """Zero-magnitude vectors yield a 0-degree angle (not a crash)."""
    # A target at the origin (range 0) gives a zero line-of-sight vector.
    solution = targeting.intercept_solution(0.0, 90.0, 45.0, 0.0, 10.0)
    assert solution.lead_angle_deg == 0.0
