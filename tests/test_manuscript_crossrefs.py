"""Bind manuscript citations and figure references to the things they name.

Two classes of reference sat outside every gate before this file existed:

* four figure cross-references were written ``{@fig:label}``, which is not
  pandoc-crossref syntax (`[@fig:label]` is). They would have rendered as
  literal braces in any built PDF while the token gate — which only looks for
  ``{{TOKEN}}`` — stayed green;
* ``references.bib`` was cited by nothing. A pandoc build with that bibliography
  emits an empty reference list, and no test noticed.

These tests are the missing binding, in both directions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = PACKAGE_ROOT / "manuscript"

_BIB_KEY_RE = re.compile(r"^@\w+\{([^,]+),", re.MULTILINE)
_CITE_RE = re.compile(r"\[@([^\]]+)\]")
_FIG_DEF_RE = re.compile(r"\{#(fig:[a-z0-9_]+)\}")
_FIG_BAD_REF_RE = re.compile(r"\{@fig:[a-z0-9_]+\}")


def _sections() -> list[Path]:
    paths = sorted(MANUSCRIPT.glob("[0-9][0-9]_*.md"))
    assert paths, "no numbered manuscript sections found"
    return paths


def _prose() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _sections())


def _bib_keys() -> set[str]:
    keys = set(_BIB_KEY_RE.findall((MANUSCRIPT / "references.bib").read_text(encoding="utf-8")))
    assert keys, "references.bib defines no keys"
    return keys


def _cited_keys(text: str) -> set[str]:
    """Every key inside a ``[@...]`` group, including ``;``-separated groups."""
    keys: set[str] = set()
    for group in _CITE_RE.findall(text):
        keys |= {part.strip().lstrip("@") for part in group.split(";") if part.strip()}
    return keys


def test_every_bib_key_is_cited_in_prose():
    """An entry nobody cites is decoration; pandoc would print an empty bibliography."""
    uncited = _bib_keys() - _cited_keys(_prose())
    assert uncited == set(), f"references.bib keys never cited in prose: {sorted(uncited)}"


def test_every_citation_resolves_to_a_bib_entry():
    """The other direction: a citation with no entry renders as a dangling key."""
    cited = {k for k in _cited_keys(_prose()) if not k.startswith("fig:")}
    assert cited, "no bibliography citations found in prose"
    dangling = cited - _bib_keys()
    assert dangling == set(), f"citations with no references.bib entry: {sorted(dangling)}"


def test_syntax_guide_lists_exactly_the_live_bib_keys():
    """`SYNTAX.md` advertises the key list; it must not drift from the file."""
    text = (MANUSCRIPT / "SYNTAX.md").read_text(encoding="utf-8")
    block = text.split("Current keys:", 1)
    assert len(block) == 2, "SYNTAX.md no longer states the current key list"
    listed = set(re.findall(r"`([a-z]+\d{4}[a-z]+)`", block[1].split("\n\n", 1)[0]))
    assert listed == _bib_keys(), f"SYNTAX.md key list drifted: {sorted(listed ^ _bib_keys())}"


def test_no_brace_style_figure_references():
    """The brace-delimited figure reference is not pandoc-crossref syntax.

    Scanned in the guides as well as the sections: the brace form was not a
    typo in §3, it was what `SYNTAX.md` told authors to write, while
    `manuscript/README.md` documented the correct bracket form. Leaving the
    guide unscanned would let the source of the defect re-seed it.
    """
    scanned = [*_sections(), MANUSCRIPT / "SYNTAX.md", MANUSCRIPT / "README.md"]
    offenders = {p.name: _FIG_BAD_REF_RE.findall(p.read_text(encoding="utf-8")) for p in scanned}
    bad = {name: hits for name, hits in offenders.items() if hits}
    assert bad == {}, f"brace-style figure references (use the bracket form): {bad}"


def test_figure_definitions_and_references_agree():
    """Every `{#fig:label}` is referenced, and every reference is defined."""
    prose = _prose()
    defined = set(_FIG_DEF_RE.findall(prose))
    referenced = {k for k in _cited_keys(prose) if k.startswith("fig:")}
    assert defined, "no figure definitions found"
    assert defined == referenced, f"figure def/ref mismatch: {sorted(defined ^ referenced)}"


def test_figure_labels_match_the_rendered_png_set():
    """Each labelled figure names a PNG that `figures.render_all` actually writes."""
    from for_your_eyes_only import figures

    prose = _prose()
    labels = {label.removeprefix("fig:") for label in _FIG_DEF_RE.findall(prose)}
    images = set(re.findall(r"!\[[^\]]*\]\(([a-z0-9_]+\.png)\)", prose))
    assert {f"{label}.png" for label in labels} == images

    rendered = {p.name for p in figures.render_all(figure_dir=PACKAGE_ROOT / "output" / "figures")}
    missing = images - rendered
    assert missing == set(), f"referenced figures no generator writes: {sorted(missing)}"


@pytest.mark.parametrize("bad", ["{@fig:dive_profile}", "{@fig:nope}"])
def test_the_brace_style_detector_actually_matches(bad):
    """Positive control: the detector fires on the exact pattern it forbids."""
    assert _FIG_BAD_REF_RE.findall(bad) == [bad]
    assert _FIG_BAD_REF_RE.findall(bad.replace("{", "[").replace("}", "]")) == []
