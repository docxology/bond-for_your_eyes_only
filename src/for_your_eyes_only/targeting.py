"""ATAC fire-control targeting: intercept lead-angle firing solution.

The ATAC targeting-communicator must direct a weapon onto a moving target.
Given the target's initial range and bearing, the target's course and speed,
and the weapon's speed, this module computes the deterministic firing
solution: the *intercept time*, the *lead angle* by which the weapon must be
aimed ahead of the line of sight, and the *closest approach* when interception
is not geometrically possible.

Real model behind the code — the classical *constant bearing, decreasing
range* pursuit/interception problem. A weapon launched at speed :math:`v_w`
from the origin meets a target at position :math:`p_0` moving with velocity
:math:`v_t` when :math:`|p_0 + v_t t| = v_w t`. Squaring both sides yields a
quadratic in the intercept time:

.. math:: (|v_t|^2 - v_w^2)\\,t^2 + 2(p_0\\cdot v_t)\\,t + |p_0|^2 = 0.

When a positive real root :math:`t_i` exists, the weapon direction is
:math:`u = (p_0 + v_t t_i) / (v_w t_i)` and the lead angle is the angle between
:math:`u` and the line of sight :math:`p_0`. When no positive root exists (the
target outruns or outmanoeuvres the weapon), the module reports the
*closest-approach* geometry instead — the point where the two trajectories
pass nearest each other.

Everything is deterministic: inputs are fixed bearings/courses (degrees) and
the result is pure trigonometry — no RNG, no wall clock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "FireControlSolution",
    "closest_approach",
    "intercept_solution",
    "normalise_course",
    "polar_to_velocity",
]

#: Small positive tolerance below which the quadratic is deemed degenerate.
_EPS = 1e-9


@dataclass(frozen=True)
class FireControlSolution:
    """The deterministic fire-control solution for one engagement."""

    target_range_m: float
    target_bearing_deg: float
    target_course_deg: float
    target_speed_ms: float
    weapon_speed_ms: float
    intercept_time_s: float
    lead_angle_deg: float
    weapon_course_deg: float
    feasible: bool
    closest_approach_m: float
    closest_approach_time_s: float

    @property
    def closed_loop(self) -> bool:
        """True when the weapon can actually close to intercept (``feasible``)."""
        return self.feasible


def normalise_course(deg: float) -> float:
    """Wrap a compass course/bearing into [0, 360) degrees (deterministic)."""
    return deg % 360.0


def polar_to_velocity(speed: float, course_deg: float) -> tuple[float, float]:
    """Convert a (speed, course) pair into a (east, north) velocity vector."""
    rad = math.radians(normalise_course(course_deg))
    east = speed * math.sin(rad)
    north = speed * math.cos(rad)
    return (east, north)


def _angle_between(u: tuple[float, float], v: tuple[float, float]) -> float:
    """Return the unsigned angle (degrees) between two vectors."""
    du = math.hypot(*u)
    dv = math.hypot(*v)
    if du < _EPS or dv < _EPS:
        return 0.0
    cosine = (u[0] * v[0] + u[1] * v[1]) / (du * dv)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def closest_approach(
    p0: tuple[float, float],
    v_t: tuple[float, float],
    v_w: tuple[float, float],
) -> tuple[float, float]:
    """Return ``(closest_approach_m, time_s)`` between weapon and target.

    The target starts at ``p0`` with velocity ``v_t``; the weapon is launched
    from the origin along ``v_w``. The relative position is
    :math:`p(t) = p_0 + (v_t - v_w) t`; closest approach occurs where the
    relative range derivative vanishes, i.e.
    :math:`t = -\\frac{p_0 \\cdot v_{rel}}{|v_{rel}|^2}`.
    """
    v_rel = (v_t[0] - v_w[0], v_t[1] - v_w[1])
    rel_sq = v_rel[0] * v_rel[0] + v_rel[1] * v_rel[1]
    if rel_sq < _EPS:
        # Parallel, equal-speed — range is constant; closest is initial range.
        return math.hypot(*p0), 0.0
    t_ca = -(p0[0] * v_rel[0] + p0[1] * v_rel[1]) / rel_sq
    t_ca = max(0.0, t_ca)
    px = p0[0] + v_rel[0] * t_ca
    py = p0[1] + v_rel[1] * t_ca
    return math.hypot(px, py), t_ca


def intercept_solution(
    target_range_m: float,
    target_bearing_deg: float,
    target_course_deg: float,
    target_speed_ms: float,
    weapon_speed_ms: float,
) -> FireControlSolution:
    """Compute the fire-control intercept solution for one engagement.

    Args:
        target_range_m: Initial target range from the weapon launcher (m).
        target_bearing_deg: Bearing of the target from the launcher (deg, 0=N).
        target_course_deg: Target's own course (deg, 0=N).
        target_speed_ms: Target speed (m/s).
        weapon_speed_ms: Weapon speed (m/s).

    Returns:
        A :class:`FireControlSolution` with the intercept time, lead angle,
        weapon course, feasibility, and closest-approach fallback.
    """
    if target_range_m < 0:
        raise ValueError("target_range_m must be >= 0")
    if target_speed_ms < 0 or weapon_speed_ms <= 0:
        raise ValueError("speeds must be non-negative / weapon speed positive")

    p0 = polar_to_velocity(target_range_m, target_bearing_deg)
    v_t = polar_to_velocity(target_speed_ms, target_course_deg)

    # Quadratic: (|v_t|^2 - v_w^2) t^2 + 2(p0.v_t) t + |p0|^2 = 0
    a = v_t[0] * v_t[0] + v_t[1] * v_t[1] - weapon_speed_ms * weapon_speed_ms
    b = 2.0 * (p0[0] * v_t[0] + p0[1] * v_t[1])
    c = p0[0] * p0[0] + p0[1] * p0[1]

    t_i: float | None = None
    weapon_course = target_bearing_deg
    lead = 0.0
    feasible = False

    if abs(a) < _EPS:
        # Weapon and target have equal speed magnitude: linear equation b t + c = 0
        if abs(b) > _EPS and c > 0:
            cand = -c / b
            if cand > 0:
                t_i = cand
    else:
        disc = b * b - 4.0 * a * c
        if disc >= 0.0:
            sqrt_disc = math.sqrt(disc)
            roots = [(-b - sqrt_disc) / (2.0 * a), (-b + sqrt_disc) / (2.0 * a)]
            positive = [r for r in roots if r > _EPS]
            if positive:
                t_i = min(positive)

    if t_i is not None:
        # Weapon closure direction u = (p0 + v_t t_i) / (v_w t_i)
        den = weapon_speed_ms * t_i
        u_east = (p0[0] + v_t[0] * t_i) / den
        u_north = (p0[1] + v_t[1] * t_i) / den
        weapon_course = math.degrees(math.atan2(u_east, u_north)) % 360.0
        lead = _angle_between(p0, (u_east, u_north))
        feasible = True

    # Closest-approach fallback geometry (always computed).
    v_w_vec = polar_to_velocity(weapon_speed_ms, weapon_course)
    ca_range, ca_time = closest_approach(p0, v_t, v_w_vec)

    return FireControlSolution(
        target_range_m=target_range_m,
        target_bearing_deg=normalise_course(target_bearing_deg),
        target_course_deg=normalise_course(target_course_deg),
        target_speed_ms=target_speed_ms,
        weapon_speed_ms=weapon_speed_ms,
        intercept_time_s=t_i if t_i is not None else math.inf,
        lead_angle_deg=lead,
        weapon_course_deg=weapon_course,
        feasible=feasible,
        closest_approach_m=ca_range,
        closest_approach_time_s=ca_time,
    )
