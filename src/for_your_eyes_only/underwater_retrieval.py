"""Underwater retrieval planning for the ATAC wreck recovery.

The mission's target device rests on the seabed at a known depth, subject to
a horizontal current. This module plans the retrieval dive: it models the
diver's descent and ascent as deterministic time profiles, compensates for
current drift so the retrieval bell reaches the wreck, and applies a
Haldane-style inert-gas tissue model to schedule a safe staged ascent.

Real models behind the code:

* **Current-drift compensation**: with a constant horizontal current
  :math:`(u, v)` and a total dive time :math:`T`, the surface point must be
  offset by :math:`-T \\cdot (u, v)` so that drift carries the bell onto the
  wreck. This is elementary ballistic-motion math, made deterministic by
  fixing the current and time.
* **Haldane tissue model**: the body is modelled as a set of independent
  tissue compartments, each with a half-time :math:`t_{1/2}`. Tissue pressure
  follows :math:`dP/dt = (P_{ambient} - P)/\\tau`, giving exponential ascent
  toward the ambient partial pressure. A decompression ceiling is computed per
  compartment (M-value) by :meth:`HaldaneModel.ceiling_m`, and the exposure at
  which the limiting compartment reaches it by
  :func:`no_decompression_limit`.
* **Ascent scheduling**: the profile is a sequence of (depth, duration) stages
  traversed bottom-up; stops are snapped to a fixed interval (e.g. 3 m).

.. warning::

    The tissue model and the ascent schedule are **not yet coupled**.
    :func:`plan_descent` stages the climb geometrically — fixed
    ``STOP_INTERVAL`` steps at fixed ``ASCENT_RATE`` — without consulting any
    compartment ceiling, so a stage boundary in a profile is not a
    decompression obligation and the profile is not a physiologically
    validated schedule. Wiring the ceiling into the staging is tracked as open
    work in ``TODO.md``.

All parameters are fixed and the computation is purely arithmetic, so dive
plans are byte-reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = [
    "DiveProfile",
    "DiveSchedule",
    "HaldaneModel",
    "RetrievalPlan",
    "RetrievalPlanner",
    "current_offset",
    "format_schedule",
    "no_decompression_limit",
    "plan_descent",
    "tissue_saturation",
]

#: Depth of the wreck below the surface (metres) — St. George's resting depth.
DEFAULT_WRECK_DEPTH = 42.0
#: Default horizontal current in metres per second (east/north components).
DEFAULT_CURRENT = (-0.12, 0.05)
#: Fixed ascent rate used to stage the decompression climb (m/s ~ 9 m/min).
ASCENT_RATE = 0.15
#: Descent rate (m/s ~ 18 m/min).
DESCENT_RATE = 0.30
#: Decompression stop interval (metres) — stops snap to multiples of this.
STOP_INTERVAL = 3.0


@dataclass(frozen=True)
class DepthStage:
    """A single segment of the dive: fixed depth over a duration (seconds)."""

    depth: float
    duration_s: float


@dataclass(frozen=True)
class DiveProfile:
    """The full deterministic dive time profile (depth vs time)."""

    descent_stages: tuple[DepthStage, ...]
    bottom_time_s: float
    ascent_stages: tuple[DepthStage, ...]
    total_time_s: float

    def max_depth(self) -> float:
        """Return the deepest point reached (the bottom stage depth)."""
        return max((s.depth for s in self.descent_stages), default=0.0)


# --------------------------------------------------------------------------- #
# Haldane tissue model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HaldaneModel:
    """A deterministic set of inert-gas tissue compartments.

    Each compartment ``i`` has a half-time ``t1_2`` (seconds) and an M-value
    coefficient ``m`` (the tissue's tolerated over-pressure per metre of
    ambient pressure above surface). The set is fixed at construction.

    An M-value must exceed 1.0: it is the *multiple* of surface pressure a
    tissue tolerates, so a value at or below 1.0 would describe a tissue that
    cannot survive being at the surface, and would make
    :func:`no_decompression_limit` return a negative exposure.
    """

    half_times: tuple[float, ...] = (34.0, 52.0, 80.0, 240.0, 360.0, 540.0)
    m_values: tuple[float, ...] = (2.72, 2.54, 2.24, 1.89, 1.68, 1.51)

    def __post_init__(self) -> None:
        if len(self.half_times) != len(self.m_values):
            raise ValueError("HaldaneModel half_times and m_values must have equal length")
        if not all(t > 0 for t in self.half_times):
            raise ValueError("HaldaneModel half_times must be positive")
        if not all(m > 1.0 for m in self.m_values):
            raise ValueError("HaldaneModel m_values must each exceed 1.0 (surface-pressure multiple)")

    def tau(self, index: int) -> float:
        """Return the time constant ``tau = t1/2 / ln(2)`` for compartment i."""
        return self.half_times[index] / math.log(2.0)

    def compartments(self) -> int:
        """Return the number of tissue compartments in the model."""
        return len(self.half_times)

    def ceiling_m(self, index: int, ambient_pressure_m: float) -> float:
        """Return the decompression ceiling (max allowed tissue over-pressure in m)."""
        return self.m_values[index] * max(ambient_pressure_m, 0.0)


def tissue_saturation(
    initial_pressure_m: float,
    ambient_pressure_m: float,
    exposure_s: float,
    half_time: float,
) -> float:
    """Return tissue pressure (m water column) after exponential supersaturation.

    Implements the closed-form Haldane saturation toward ``ambient_pressure_m``
    from ``initial_pressure_m`` over ``exposure_s`` seconds.
    """
    tau = half_time / math.log(2.0)
    return ambient_pressure_m + (initial_pressure_m - ambient_pressure_m) * math.exp(-exposure_s / tau)


def no_decompression_limit(model: HaldaneModel, depth_m: float) -> float:
    """Return the maximum bottom time (s) allowed without decompression stops.

    Uses the classical *surface M-value* criterion. Ambient absolute pressure
    is ``1 + depth/10`` atmospheres (surface = 1 atm). Each compartment starts
    saturated at the surface and on-gasses toward the ambient pressure with
    time constant ``tau``. The tissue may not exceed its tolerated surface
    supersaturation ``M_i`` (an over-pressure multiple). The no-decompression
    limit is the exposure at which the *limiting* (fastest-relevant)
    compartment first saturates to ``M_i``:

    .. math:: t_i = -\\tau_i \\ln\\frac{P_{amb}-M_i}{P_{amb}-1}

    A compartment that never reaches ``M_i`` at this depth (``P_amb <= M_i``)
    imposes no limit. Returns ``inf`` at or above the surface, and otherwise
    the smallest limiting exposure — which is itself ``inf`` when the depth is
    shallow enough that no compartment can ever reach its ceiling.
    """
    ambient = 1.0 + depth_m / 10.0  # absolute pressure in atmospheres
    if ambient <= 1.0:
        return math.inf
    limiting = math.inf
    for index in range(model.compartments()):
        m_value = model.m_values[index]
        if ambient <= m_value:
            continue  # this tissue never reaches its surface supersaturation
        # Past the guard above, num = ambient - m_value > 0, and den =
        # ambient - 1 > 0 because ambient > 1; the logarithm is therefore
        # always well defined here and needs no further guard.
        num = ambient - m_value
        den = ambient - 1.0
        exposure = model.tau(index) * math.log(den / num)
        limiting = min(limiting, exposure)
    return limiting


# --------------------------------------------------------------------------- #
# Descent / ascent planning
# --------------------------------------------------------------------------- #


def plan_descent(
    depth_m: float,
    *,
    descent_rate: float = DESCENT_RATE,
    bottom_time_s: float = 600.0,
) -> DiveProfile:
    """Plan a deterministic dive: descent, bottom, then a staged ascent.

    The ascent is decomposed into fixed ``STOP_INTERVAL``-snapped stages, each
    traversed at ``ASCENT_RATE``. The profile is fully deterministic.

    .. warning::

        This schedule is **geometric, not physiological**. It does not consult
        :class:`HaldaneModel`, :func:`no_decompression_limit`, or any tissue
        ceiling — stop depths and durations are fixed by ``STOP_INTERVAL`` and
        ``ASCENT_RATE`` alone. The tissue model in this module is exercised
        separately (see :func:`no_decompression_limit`) and is not yet wired
        into ascent staging. Do not read a stage boundary here as a
        decompression obligation.

    Args:
        depth_m: Wreck depth (metres, > 0).
        descent_rate: Descent speed (m/s).
        bottom_time_s: Time spent working at the wreck before ascent.

    Returns:
        A :class:`DiveProfile` of descent/bottom/ascent stages.
    """
    if depth_m <= 0:
        raise ValueError("depth_m must be > 0")
    if descent_rate <= 0:
        raise ValueError("descent_rate must be > 0")
    if bottom_time_s < 0:
        raise ValueError("bottom_time_s must be >= 0")

    descent_time = depth_m / descent_rate

    ascent_stages: list[DepthStage] = []
    ascent_time = 0.0
    depth = depth_m
    # Climb to the surface in fixed STOP_INTERVAL steps. Deliberately geometric:
    # no tissue-model consultation happens here (see the docstring warning).
    while depth > 0.0:
        step = min(depth, STOP_INTERVAL)
        segment_time = step / ASCENT_RATE
        ascent_stages.append(DepthStage(depth=depth, duration_s=segment_time))
        ascent_time += segment_time
        depth -= step

    total_time = descent_time + bottom_time_s + ascent_time
    descent_stages = (DepthStage(depth=depth_m, duration_s=descent_time),)
    return DiveProfile(
        descent_stages=descent_stages,
        bottom_time_s=bottom_time_s,
        ascent_stages=tuple(ascent_stages),
        total_time_s=total_time,
    )


def current_offset(current: tuple[float, float], duration_s: float) -> tuple[float, float]:
    """Return the horizontal surface offset (east, north) drift causes.

    With a constant current and total dive time ``duration_s``, a target fixed
    on the seabed drifts by ``-duration_s * current`` relative to a stationary
    bell; the bell must therefore *start* at ``duration_s * current`` upstream.
    """
    east, north = current
    return (east * duration_s, north * duration_s)


@dataclass(frozen=True)
class RetrievalPlan:
    """The complete retrieval plan: profile, drift, and target offset."""

    profile: DiveProfile
    current: tuple[float, float]
    surface_offset: tuple[float, float]
    target_reachable: bool

    @property
    def total_time_s(self) -> float:
        return self.profile.total_time_s


@dataclass(frozen=True)
class DiveSchedule:
    """A human-readable, deterministic schedule of the dive stages."""

    rows: tuple[tuple[str, float, float], ...] = field(default_factory=tuple)


def format_schedule(profile: DiveProfile) -> DiveSchedule:
    """Flatten a :class:`DiveProfile` into an ordered (phase, depth, time) schedule.

    The bottom row always carries the profile's maximum depth. A zero bottom
    time means the diver spent no time there, not that the bottom was at the
    surface, so the depth column stays truthful either way.
    """
    rows: list[tuple[str, float, float]] = []
    for stage in profile.descent_stages:
        rows.append(("descent", stage.depth, stage.duration_s))
    rows.append(("bottom", profile.max_depth(), profile.bottom_time_s))
    for stage in profile.ascent_stages:
        rows.append(("ascent", stage.depth, stage.duration_s))
    return DiveSchedule(tuple(rows))


class RetrievalPlanner:
    """Deterministic planner binding current and depth into a retrieval plan.

    Use :meth:`plan` to produce a :class:`RetrievalPlan`; the plan is a pure
    function of the inputs (no RNG), so identical calls give identical plans.
    """

    def __init__(
        self,
        *,
        wreck_depth: float = DEFAULT_WRECK_DEPTH,
        current: tuple[float, float] = DEFAULT_CURRENT,
        bottom_time_s: float = 600.0,
        max_offset_m: float = 200.0,
    ) -> None:
        self.wreck_depth = wreck_depth
        self.current = current
        self.bottom_time_s = bottom_time_s
        self.max_offset_m = max_offset_m
        if wreck_depth <= 0:
            raise ValueError("wreck_depth must be > 0")

    def plan(self) -> RetrievalPlan:
        """Compute the retrieval plan for this planner's fixed inputs."""
        profile = plan_descent(self.wreck_depth, bottom_time_s=self.bottom_time_s)
        offset = current_offset(self.current, profile.total_time_s)
        reach = math.hypot(*offset) <= self.max_offset_m
        return RetrievalPlan(
            profile=profile,
            current=self.current,
            surface_offset=offset,
            target_reachable=reach,
        )
