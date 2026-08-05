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


def _two_option_graph() -> ir.IslandGraph:
    """A graph with a short-risky and a long-safe corridor between the same ends.

    Real data, explicit and checkable by hand: base -> beacon -> landing is
    20 nm at risk 5.0 per leg; base -> channel -> landing is 26 nm at risk 0.1
    per leg. At risk_weight 0 the short corridor wins by 6 nm; by risk_weight
    1.0 the risk term (9.8 nm-equivalent) has overtaken it.
    """
    nodes = {
        "base": (0.0, 0.0),
        "beacon": (5.0, 0.0),
        "channel": (0.0, 6.0),
        "landing": (10.0, 0.0),
    }
    adjacency = {
        "base": (ir.Edge("beacon", 10.0, 5.0), ir.Edge("channel", 13.0, 0.1)),
        "beacon": (ir.Edge("base", 10.0, 5.0), ir.Edge("landing", 10.0, 5.0)),
        "channel": (ir.Edge("base", 13.0, 0.1), ir.Edge("landing", 13.0, 0.1)),
        "landing": (ir.Edge("beacon", 10.0, 5.0), ir.Edge("channel", 13.0, 0.1)),
    }
    return ir.IslandGraph(nodes=nodes, adjacency=adjacency)


def test_risk_weight_changes_the_chosen_path():
    """The risk term must be able to *decide* a route, not merely price one.

    Asserting `high.total_cost >= low.distance_nm` (the previous assertion)
    holds for any non-negative risk weight and any graph, including one where
    `risk_weight` was ignored entirely. This drives the mechanism: the same
    origin/destination pair must resolve to two different paths.
    """
    graph = _two_option_graph()
    reckless = ir.plan_route(graph, "base", "landing", risk_weight=0.0)
    cautious = ir.plan_route(graph, "base", "landing", risk_weight=5.0)

    assert reckless.path == ("base", "beacon", "landing")
    assert cautious.path == ("base", "channel", "landing")
    assert reckless.path != cautious.path
    # The safe route is genuinely longer — the planner traded distance for risk.
    assert cautious.distance_nm > reckless.distance_nm


def test_ionian_graph_route_is_risk_invariant():
    """On the shipped graph, risk never changes the route — only its cost.

    Stated as a pinned fact rather than left implied. The least-distance and
    least-risk corridors coincide for every node pair in the Ionian graph, so
    no route in this package demonstrates risk-driven path selection; the
    mechanism is exercised on `_two_option_graph` instead. If the graph is ever
    edited so that risk does steer a route, this test fails and the claim in
    `island_routing`'s module docstring must be revisited.
    """
    graph = ir.build_ionian_graph()
    pairs = [(a, b) for a in sorted(graph.nodes) for b in sorted(graph.nodes) if a < b]
    assert len(pairs) == 28
    for origin, destination in pairs:
        low = ir.plan_route(graph, origin, destination, risk_weight=0.0)
        high = ir.plan_route(graph, origin, destination, risk_weight=50.0)
        assert low.path == high.path, f"{origin}->{destination} route changed with risk weight"
        # Cost still responds to the weight even where the path does not.
        assert high.total_cost > low.total_cost


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
