"""Tests for the deterministic figure generators."""

from pathlib import Path


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
