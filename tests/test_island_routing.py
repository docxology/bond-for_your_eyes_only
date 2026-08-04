"""Real-data tests for the Greek-island insertion routing module."""

import math

import pytest

from for_your_eyes_only import island_routing as ir


def test_build_ionian_graph_has_nodes():
    graph = ir.build_ionian_graph()
    for node in ("corfu", "paxi", "lefkada", "ithaca", "kefalonia", "zakynthos", "wreck_site", "mainland"):
        assert graph.has_node(node)
    # every node has at least one neighbour
    for node in graph.nodes:
        assert graph.neighbors(node)


def test_plan_route_returns_path():
    graph = ir.build_ionian_graph()
    route = ir.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0)
    assert route.path[0] == "corfu"
    assert route.path[-1] == "wreck_site"
    assert len(route.path) >= 2
    assert route.hops == len(route.path) - 1
    assert route.total_cost > 0
    assert route.distance_nm > 0


def test_plan_route_astar_equals_dijkstra():
    graph = ir.build_ionian_graph()
    a = ir.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0, use_astar=True)
    d = ir.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0, use_astar=False)
    assert a.path == d.path
    assert a.total_cost == pytest.approx(d.total_cost)


def test_plan_route_risk_sensitivity():
    """Higher risk weight can change the chosen path (safer route)."""
    graph = ir.build_ionian_graph()
    low = ir.plan_route(graph, "corfu", "zakynthos", risk_weight=0.0)
    high = ir.plan_route(graph, "corfu", "zakynthos", risk_weight=50.0)
    # risk-averse planner may route via lower-risk corridor; distance may grow
    assert high.total_cost >= low.distance_nm
    assert isinstance(high.path, tuple)


def test_plan_route_deterministic():
    graph = ir.build_ionian_graph()
    a = ir.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0)
    b = ir.plan_route(graph, "corfu", "wreck_site", risk_weight=1.0)
    assert a == b


def test_plan_route_unknown_node_raises():
    graph = ir.build_ionian_graph()
    with pytest.raises(KeyError):
        ir.plan_route(graph, "atlantis", "wreck_site")
    with pytest.raises(KeyError):
        ir.plan_route(graph, "corfu", "atlantis")


def test_route_connected_edges_exist():
    """Adjacent nodes in a route must be connected by an edge."""
    graph = ir.build_ionian_graph()
    route = ir.plan_route(graph, "corfu", "wreck_site")
    for i in range(len(route.path) - 1):
        a, b = route.path[i], route.path[i + 1]
        assert any(e.destination == b for e in graph.neighbors(a))


def test_make_route_cost():
    cost = ir.make_route_cost(risk_weight=2.0)
    assert cost(10.0, 0.5) == pytest.approx(11.0)
    no_risk = ir.make_route_cost(risk_weight=0.0)
    assert no_risk(10.0, 100.0) == pytest.approx(10.0)


def test_straight_line_and_heuristic():
    graph = ir.build_ionian_graph()
    d = graph.straight_line("corfu", "paxi")
    assert d == pytest.approx(math.hypot(4.0 - 0.0, 6.0 - 14.0))
    assert d > 0
