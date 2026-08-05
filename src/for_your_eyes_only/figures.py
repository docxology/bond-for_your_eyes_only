"""Deterministic figure generation for the ATAC mission.

Renders publication-quality figures for the mission's concepts, all fully
deterministic (matplotlib ``Agg`` backend, fixed data from the domain modules,
no RNG). Each generator returns the absolute path of the written PNG.

Figures (all four written by :func:`render_all`):

* :func:`render_island_graph` — the Ionian insertion graph with the planned
  route highlighted.
* :func:`render_dive_profile` — the underwater retrieval dive depth/time
  profile with current-drift offset annotation.
* :func:`render_targeting_geometry` — the fire-control intercept geometry:
  line of sight, weapon course, and target velocity.
* :func:`render_acoustic_link` — the acoustic link SNR-vs-range curve with the
  detection threshold, operating point, and maximum closure range.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; deterministic render

import matplotlib.axes
import matplotlib.pyplot as plt  # noqa: E402

from for_your_eyes_only import acoustic_link, island_routing, targeting, underwater_retrieval
from for_your_eyes_only.mission import ATAC_LINK, ATAC_LINK_RANGE_M

#: Canonical figures output directory (under the package ``output/`` tree).
DEFAULT_FIGURE_DIR = Path(__file__).resolve().parents[2] / "output" / "figures"


def _label(ax: matplotlib.axes.Axes) -> None:
    ax.set_xlabel("East (nm)")
    ax.set_ylabel("North (nm)")


def render_island_graph(
    *,
    output_path: str | Path | None = None,
    origin: str = "corfu",
    destination: str = "wreck_site",
    risk_weight: float = 1.0,
) -> Path:
    """Render the Ionian island graph with the planned insertion route."""
    dest = Path(output_path) if output_path is not None else DEFAULT_FIGURE_DIR / "island_graph.png"
    dest.parent.mkdir(parents=True, exist_ok=True)

    graph = island_routing.build_ionian_graph()
    route = island_routing.plan_route(graph, origin, destination, risk_weight=risk_weight)

    fig, ax = plt.subplots(figsize=(8, 6))
    route_set = set(zip(route.path, route.path[1:])) | set(zip(route.path[1:], route.path))
    for node, edges in graph.adjacency.items():
        nx, ny = graph.nodes[node]
        for edge in edges:
            ex, ey = graph.nodes[edge.destination]
            # edge (a,b) is drawn once; only the route is highlighted
            if (node, edge.destination) in route_set:
                ax.plot([nx, ex], [ny, ey], color="#c0392b", lw=2.5, alpha=0.9)
            else:
                ax.plot([nx, ex], [ny, ey], color="#bdc3c7", lw=1.0, ls="--")
    for node, (x, y) in graph.nodes.items():
        colour = "#e74c3c" if node in route.path else "#2980b9"
        ax.plot(x, y, "o", color=colour, ms=8, zorder=5)
        ax.annotate(node, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9)

    ax.set_title(f"For Your Eyes Only — Ionian insertion route: {origin} -> {destination}")
    _label(ax)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    return dest


def render_dive_profile(
    *,
    output_path: str | Path | None = None,
    wreck_depth: float = underwater_retrieval.DEFAULT_WRECK_DEPTH,
) -> Path:
    """Render the underwater retrieval dive depth-vs-time profile."""
    dest = Path(output_path) if output_path is not None else DEFAULT_FIGURE_DIR / "dive_profile.png"
    dest.parent.mkdir(parents=True, exist_ok=True)

    planner = underwater_retrieval.RetrievalPlanner(wreck_depth=wreck_depth)
    plan = planner.plan()
    profile = plan.profile

    # Rebuild the schedule as (time_start, depth).
    times: list[float] = [0.0]
    depths: list[float] = [0.0]
    t = 0.0
    for stage in profile.descent_stages:
        t += stage.duration_s
        times.append(t)
        depths.append(stage.depth)
    t += profile.bottom_time_s
    times.append(t)
    depths.append(profile.max_depth())
    for stage in sorted(profile.ascent_stages, key=lambda s: -s.duration_s):
        t += stage.duration_s
        times.append(t)
        depths.append(max(0.0, depths[-1] - stage.depth))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times, [-d for d in depths], color="#2980b9", lw=2)
    ax.fill_between(times, [-d for d in depths], 0, color="#3498db", alpha=0.2)
    ax.axhline(-planner.wreck_depth, color="#c0392b", ls="--", alpha=0.6)
    ax.set_title("For Your Eyes Only — underwater retrieval dive profile")
    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel("Depth (m, negative below surface)")
    ax.annotate(
        f"current offset ≈ ({plan.surface_offset[0]:.2f}, {plan.surface_offset[1]:.2f}) m · "
        f"reachable={plan.target_reachable}",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", fc="white", alpha=0.8),
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    return dest


def render_targeting_geometry(
    *,
    output_path: str | Path | None = None,
    target_range_m: float = 4000.0,
    target_bearing_deg: float = 45.0,
    target_course_deg: float = 120.0,
    target_speed_ms: float = 8.0,
    weapon_speed_ms: float = 45.0,
) -> Path:
    """Render the fire-control intercept geometry for the ATAC targeting solution."""
    dest = Path(output_path) if output_path is not None else DEFAULT_FIGURE_DIR / "targeting_geometry.png"
    dest.parent.mkdir(parents=True, exist_ok=True)

    solution = targeting.intercept_solution(
        target_range_m=target_range_m,
        target_bearing_deg=target_bearing_deg,
        target_course_deg=target_course_deg,
        target_speed_ms=target_speed_ms,
        weapon_speed_ms=weapon_speed_ms,
    )
    # Geometry in the plane.
    tx = target_range_m * math.sin(math.radians(target_bearing_deg))
    ty = target_range_m * math.cos(math.radians(target_bearing_deg))
    # Weapon velocity vector from the solution course.
    w_east = weapon_speed_ms * math.sin(math.radians(solution.weapon_course_deg))
    w_north = weapon_speed_ms * math.cos(math.radians(solution.weapon_course_deg))
    t_east, t_north = targeting.polar_to_velocity(target_speed_ms, target_course_deg)

    fig, ax = plt.subplots(figsize=(7, 7))
    # line of sight from launcher (0,0) to target
    ax.plot([0, tx], [0, ty], color="#2980b9", lw=2, label="line of sight")
    # weapon course vector (scaled)
    ax.arrow(0, 0, w_east * 20, w_north * 20, head_width=80, color="#c0392b", label="weapon course")
    # target velocity vector
    ax.arrow(tx, ty, t_east * 250, t_north * 250, head_width=80, color="#27ae60", label="target velocity")
    ax.plot([tx], [ty], "o", color="#e74c3c", ms=10, zorder=5)
    ax.plot([0], [0], "o", color="#2c3e50", ms=10, zorder=5)
    ax.annotate("launcher", (0, 0), xytext=(8, 8), textcoords="offset points")
    ax.annotate("target", (tx, ty), xytext=(8, 8), textcoords="offset points")

    feasible = solution.feasible
    fe_label = "feasible" if feasible else "not feasible (closest approach shown)"
    ax.set_title(f"ATAC fire-control intercept — lead angle {solution.lead_angle_deg:.2f}° ({fe_label})")
    ax.set_xlabel("East (m)")
    ax.set_ylabel("North (m)")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.3)
    ax.axis("equal")
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    return dest


def render_acoustic_link(
    *,
    output_path: str | Path | None = None,
    link: acoustic_link.AcousticLink | None = None,
    range_m: float = ATAC_LINK_RANGE_M,
) -> Path:
    """Render the underwater acoustic link SNR-vs-range curve and closure point."""
    dest = Path(output_path) if output_path is not None else DEFAULT_FIGURE_DIR / "acoustic_link.png"
    dest.parent.mkdir(parents=True, exist_ok=True)

    link = link if link is not None else ATAC_LINK
    max_range = acoustic_link.max_link_range(link)
    # A link that never closes reports max_range 0.0; still sweep out past the
    # operating range so the figure shows *why* it fails rather than going blank.
    sweep_to = max(max_range * 1.5, range_m * 1.5, 1000.0)
    ranges = [float(r) for r in range(100, int(sweep_to), 100)]
    snr_curve = [acoustic_link.received_snr(link, r) for r in ranges]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([r / 1000.0 for r in ranges], snr_curve, color="#2980b9", lw=2)
    ax.axhline(link.detection_threshold_db, color="#c0392b", ls="--", alpha=0.8, label="detection threshold")
    op_snr = acoustic_link.received_snr(link, range_m)
    ax.plot(
        [range_m / 1000.0],
        [op_snr],
        "o",
        color="#27ae60",
        ms=9,
        zorder=5,
        label=f"operating ({range_m / 1000:.1f} km, {op_snr:.1f} dB)",
    )
    ax.axvline(max_range / 1000.0, color="#8e44ad", ls=":", alpha=0.7, label=f"max range {max_range / 1000:.1f} km")
    ax.set_title(f"ATAC underwater acoustic link budget ({link.frequency_khz:.0f} kHz)")
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Received SNR (dB)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    return dest


def render_all(*, figure_dir: str | Path | None = None) -> tuple[Path, ...]:
    """Render every default figure; returns the written paths (sorted)."""
    base = Path(figure_dir) if figure_dir is not None else DEFAULT_FIGURE_DIR
    paths = [
        render_island_graph(output_path=base / "island_graph.png"),
        render_dive_profile(output_path=base / "dive_profile.png"),
        render_targeting_geometry(output_path=base / "targeting_geometry.png"),
        render_acoustic_link(output_path=base / "acoustic_link.png"),
    ]
    return tuple(sorted(paths))
