"""Greek-island insertion routing for the ATAC mission.

The operational base feeds an insertion route across the Ionian islands toward
the wreck's vicinity. This module treats the islands and mainland harbours as
a weighted graph and plans a deterministic least-cost insertion route.

Real models behind the code:

* **Weighted island graph**: nodes are harbours/locations with real
  approximate positions; edges carry a *distance* (nautical miles) and a
  *risk* weight. Both are fixed constants, so routing is reproducible.
* **Dijkstra's algorithm**: finds the minimum-total-cost path from an origin
  to a destination over non-negative edge weights. Cost is a configurable
  blend of distance and risk (``risk_weight``), so the planner can prefer the
  safe passage over the shortest one.
* **A*** : when a straight-line heuristic is provided, the search uses the
  admissible lower bound ``distance / max_speed`` to prune, returning the same
  optimal path faster — and deterministically.

The graph is deliberately small and explicit (real Ionian geography), so
verification is by inspection as well as by test.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Callable

__all__ = [
    "IslandGraph",
    "RoutePlan",
    "build_ionian_graph",
    "make_route_cost",
    "plan_route",
]


#: Cost between two nodes: direct distance (nm) and traversal risk weight.
@dataclass(frozen=True)
class Edge:
    destination: str
    distance_nm: float
    risk: float


@dataclass(frozen=True)
class IslandGraph:
    """A weighted undirected graph of island harbours/locations.

    ``nodes`` maps a name to a fixed ``(x, y)`` position (nautical-mile grid),
    and ``adjacency`` maps a name to its incident edges. Built deterministically
    from static data; not mutated after construction.
    """

    nodes: dict[str, tuple[float, float]]
    adjacency: dict[str, tuple[Edge, ...]]

    def neighbors(self, node: str) -> tuple[Edge, ...]:
        """Return the outgoing edges of ``node`` (empty tuple if unknown)."""
        return self.adjacency.get(node, ())

    def has_node(self, node: str) -> bool:
        return node in self.nodes

    def straight_line(self, a: str, b: str) -> float:
        """Euclidean distance between two nodes' fixed positions (nm)."""
        ax, ay = self.nodes[a]
        bx, by = self.nodes[b]
        return math.hypot(bx - ax, by - ay)


# --------------------------------------------------------------------------- #
# Ionian graph (real approximate geography)
# --------------------------------------------------------------------------- #


def _edges(*pairs: tuple[str, str, float, float]) -> dict[str, list[Edge]]:
    adj: dict[str, list[Edge]] = {}
    for a, b, dist, risk in pairs:
        adj.setdefault(a, []).append(Edge(b, dist, risk))
        adj.setdefault(b, []).append(Edge(a, dist, risk))
    return adj


def build_ionian_graph() -> IslandGraph:
    """Build the fixed Ionian-island insertion graph.

    Nodes are placed on an arbitrary nautical-mile plane; edges carry real-ish
    inter-island distances and a nominal risk. Deterministic: no RNG, no input.
    """
    nodes = {
        # (x, y) in nautical-mile grid
        "corfu": (0.0, 14.0),
        "paxi": (4.0, 6.0),
        "lefkada": (2.0, -4.0),
        "ithaca": (-2.0, -10.0),
        "kefalonia": (-6.0, -16.0),
        "zakynthos": (-10.0, -26.0),
        "wreck_site": (1.0, -20.0),
        "mainland": (-14.0, 0.0),
    }
    adjacency = _edges(
        ("corfu", "mainland", 38.0, 0.6),
        ("corfu", "paxi", 9.0, 0.2),
        ("paxi", "lefkada", 18.0, 0.2),
        ("paxi", "mainland", 30.0, 0.5),
        ("lefkada", "ithaca", 14.0, 0.2),
        ("lefkada", "mainland", 42.0, 0.7),
        ("ithaca", "kefalonia", 8.0, 0.1),
        ("kefalonia", "zakynthos", 20.0, 0.2),
        ("kefalonia", "wreck_site", 12.0, 0.3),
        ("zakynthos", "wreck_site", 14.0, 0.4),
        ("ithaca", "wreck_site", 15.0, 0.4),
    )
    return IslandGraph(
        nodes=nodes,
        adjacency={name: tuple(edges) for name, edges in adjacency.items()},
    )


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #


def make_route_cost(*, risk_weight: float = 1.0) -> Callable[[float, float], float]:
    """Return an edge-cost function ``distance_nm + risk_weight * risk``.

    ``risk_weight=0`` makes cost purely distance; larger values favour safer
    (lower-risk) passages at the price of distance.
    """

    def cost(distance_nm: float, risk: float) -> float:
        return distance_nm + risk_weight * risk

    return cost


@dataclass(frozen=True)
class RoutePlan:
    """A deterministic insertion route: ordered nodes plus total cost."""

    path: tuple[str, ...]
    total_cost: float
    distance_nm: float

    @property
    def hops(self) -> int:
        """Number of edge traversals in the route."""
        return max(0, len(self.path) - 1)


def _heuristic(graph: IslandGraph, goal: str) -> Callable[[str], float]:
    def h(node: str) -> float:
        return graph.straight_line(node, goal)

    return h


def plan_route(
    graph: IslandGraph,
    origin: str,
    destination: str,
    *,
    risk_weight: float = 1.0,
    use_astar: bool = True,
) -> RoutePlan:
    """Plan the minimum-cost route from ``origin`` to ``destination``.

    Uses Dijkstra (or A* with a straight-line admissible heuristic when
    ``use_astar``). Edge cost is ``distance + risk_weight * risk``. Raises
    ``KeyError`` for unknown nodes and ``ValueError`` when no route exists.

    Args:
        graph: The island graph.
        origin: Starting node.
        destination: Target node.
        risk_weight: How strongly risk penalises an edge (see
            :func:`make_route_cost`).
        use_astar: Use the A* heuristic (default True) — same optimum, faster.

    Returns:
        A :class:`RoutePlan` with the ordered path and costs.
    """
    if origin not in graph.nodes or destination not in graph.nodes:
        raise KeyError(f"unknown island node: origin={origin!r} destination={destination!r}")
    cost_fn = make_route_cost(risk_weight=risk_weight)
    h = _heuristic(graph, destination) if use_astar else (lambda _node: 0.0)

    dist: dict[str, float] = {origin: 0.0}
    prev: dict[str, str] = {}
    frontier: list[tuple[float, float, str]] = [(h(origin), 0.0, origin)]
    visited: set[str] = set()

    while frontier:
        _f, current_cost, node = heapq.heappop(frontier)
        if node in visited:
            continue
        if node == destination:
            break
        visited.add(node)
        d_node = dist[node]
        for edge in graph.neighbors(node):
            new_cost = d_node + cost_fn(edge.distance_nm, edge.risk)
            if new_cost < dist.get(edge.destination, math.inf):
                dist[edge.destination] = new_cost
                prev[edge.destination] = node
                heapq.heappush(frontier, (new_cost + h(edge.destination), new_cost, edge.destination))

    if destination not in dist:
        raise ValueError(f"no route from {origin!r} to {destination!r}")

    path: list[str] = [destination]
    cur = destination
    while cur != origin:
        cur = prev[cur]
        path.append(cur)
    path.reverse()

    total_distance = sum(_edge_distance(graph, path[i], path[i + 1]) for i in range(len(path) - 1))
    return RoutePlan(path=tuple(path), total_cost=dist[destination], distance_nm=total_distance)


def _edge_distance(graph: IslandGraph, a: str, b: str) -> float:
    for edge in graph.neighbors(a):
        if edge.destination == b:
            return edge.distance_nm
    return graph.straight_line(a, b)
