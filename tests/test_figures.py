"""Tests for the deterministic figure generators."""

from pathlib import Path

import pytest

from for_your_eyes_only import figures


def test_render_island_graph_writes_png(tmp_path):
    out = figures.render_island_graph(output_path=tmp_path / "island.png")
    assert out == tmp_path / "island.png"
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic


def test_render_dive_profile_writes_png(tmp_path):
    out = figures.render_dive_profile(output_path=tmp_path / "dive.png")
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_all_writes_all(tmp_path):
    paths = figures.render_all(figure_dir=tmp_path)
    assert len(paths) == 4
    for p in paths:
        assert p.is_file()
        assert p.stat().st_size > 0


def test_render_targeting_geometry_writes_png(tmp_path):
    out = figures.render_targeting_geometry(output_path=tmp_path / "t.png")
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_acoustic_link_writes_png(tmp_path):
    out = figures.render_acoustic_link(output_path=tmp_path / "a.png")
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_deterministic_bytes(tmp_path):
    out_a = figures.render_island_graph(output_path=tmp_path / "a.png")
    out_b = figures.render_island_graph(output_path=tmp_path / "b.png")
    assert out_a.read_bytes() == out_b.read_bytes()


def test_default_figure_dir_is_absolute():
    assert Path(figures.DEFAULT_FIGURE_DIR).is_absolute()


def test_dive_profile_series_traces_the_staged_ascent():
    """The plotted curve must be the profile the planner computed, stage by stage.

    A PNG-magic-bytes assertion cannot see a wrong curve. This binds the series
    instead: the ascent must descend through every intermediate stop depth and
    only reach the surface on the final stage. The earlier renderer subtracted
    each stage's own depth from the running depth, which drove the curve to 0 m
    on the first ascent step and then held it flat for the remaining stages —
    a figure that contradicted the profile it claimed to show.
    """
    from for_your_eyes_only import underwater_retrieval as uw

    profile = uw.plan_descent(42.0, bottom_time_s=600.0)
    times, depths = figures.dive_profile_series(profile)

    assert len(times) == len(depths)
    # One point per stage, plus the surface start, the bottom arrival, and the
    # end of bottom time.
    assert len(depths) == 2 + len(profile.descent_stages) + len(profile.ascent_stages)
    assert times == sorted(times)
    assert times[-1] == pytest.approx(profile.total_time_s)

    # Descent reaches the wreck; the bottom is held at depth.
    assert depths[1] == pytest.approx(42.0)
    assert depths[2] == pytest.approx(42.0)

    ascent_depths = depths[3:]
    # Every intermediate stop depth appears, in order, and only the last is 0.
    assert ascent_depths == pytest.approx([s.depth for s in profile.ascent_stages[1:]] + [0.0])
    assert ascent_depths[0] == pytest.approx(42.0 - uw.STOP_INTERVAL)
    assert all(d > 0.0 for d in ascent_depths[:-1]), "ascent must not jump to the surface early"
    assert ascent_depths[-1] == 0.0

    # The plotted climb rate matches the coded ASCENT_RATE on every stage.
    for i in range(len(ascent_depths)):
        dt = times[3 + i] - times[2 + i]
        drop = depths[2 + i] - ascent_depths[i]
        assert drop / dt == pytest.approx(uw.ASCENT_RATE)
