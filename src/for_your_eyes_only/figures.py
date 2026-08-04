"""Deterministic figure generation for the ATAC mission.

Renders publication-quality figures for the mission's concepts, all fully
deterministic (matplotlib ``Agg`` backend, fixed data from the domain modules,
no RNG). Each generator returns the absolute path of the written PNG.

Figures:

* :func:`render_island_graph` — the Ionian insertion graph with the planned
  route highlighted.
* :func:`render_dive_profile` — the underwater retrieval dive depth/time
  profile with current-drift offset annotation.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; deterministic render

import matplotlib.axes
import matplotlib.pyplot as plt  # noqa: E402

from for_your_eyes_only import island_routing, underwater_retrieval

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


def render_all(*, figure_dir: str | Path | None = None) -> tuple[Path, ...]:
    """Render every default figure; returns the written paths (sorted)."""
    base = Path(figure_dir) if figure_dir is not None else DEFAULT_FIGURE_DIR
    paths = [
        render_island_graph(output_path=base / "island_graph.png"),
        render_dive_profile(output_path=base / "dive_profile.png"),
    ]
    return tuple(sorted(paths))
