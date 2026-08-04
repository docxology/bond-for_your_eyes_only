"""Tests for manuscript variable hydration and the token cross-reference gate."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from for_your_eyes_only import manuscript_variables as mv

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _all_prose_tokens(manuscript_dir: Path) -> set[str]:
    """All distinct {{TOKEN}}s in numbered prose sections only."""
    tokens: set[str] = set()
    for path in sorted(manuscript_dir.glob("[0-9][0-9]_*.md")):
        tokens |= set(_TOKEN_RE.findall(path.read_text(encoding="utf-8")))
    return tokens


def test_generate_variables_strict_mode():
    variables = mv.generate_variables(require_outputs=True)
    # live result tokens are present and non-N/A
    assert variables["RESULT_RECOVERED_MATCH"] == "True"
    assert variables["RESULT_ESCROW_KEY"].isdigit()
    assert variables["RESULT_ROUTE"].startswith("corfu")
    assert variables["RESULT_TARGET_REACHABLE"] == "True"
    assert variables["BOND_CODENAME"] == "ATAC"
    assert variables["BOND_IDENTITY"] == "for_your_eyes_only"
    assert variables["CONFIG_NUM_KEYWORDS"].isdigit()


def test_generate_variables_deterministic():
    a = mv.generate_variables(now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    b = mv.generate_variables(now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert a == b


def test_generate_variables_timestamp_injectable():
    variables = mv.generate_variables(now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert variables["GENERATION_TIMESTAMP"] == "2026-01-01T00:00:00+00:00"


def test_load_manuscript_config_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        mv.load_manuscript_config(tmp_path / "nope.yaml")


def test_all_prose_tokens_are_generated():
    """Every {{TOKEN}} in prose sections must exist in generate_variables()."""
    variables = mv.generate_variables(require_outputs=True)
    prose_tokens = _all_prose_tokens(PACKAGE_ROOT / "manuscript")
    assert prose_tokens, "no tokens found in manuscript sections"
    missing = prose_tokens - set(variables.keys())
    assert not missing, f"prose tokens missing from generate_variables(): {sorted(missing)}"


def test_resolve_manuscript_tree_substitutes_all(tmp_path):
    """Resolving the tree leaves no raw {{TOKEN}} and writes every section."""
    variables = mv.generate_variables(require_outputs=True)
    out_dir, names = mv.resolve_manuscript_tree(
        variables, manuscript_dir=PACKAGE_ROOT / "manuscript", output_dir=tmp_path / "manuscript"
    )
    assert out_dir == tmp_path / "manuscript"
    assert names
    for name in names:
        text = (out_dir / name).read_text(encoding="utf-8")
        assert _TOKEN_RE.findall(text) == [], f"unresolved tokens remain in {name}"


def test_resolve_strict_leftover_raises(tmp_path):
    """An unknown token in a prose file triggers strict failure."""
    (tmp_path / "03_results.md").write_text("value is {{NO_SUCH_TOKEN}}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mv.resolve_manuscript_tree({"A": "1"}, manuscript_dir=tmp_path, output_dir=tmp_path / "o")


def test_generate_json_serializable(tmp_path):
    variables = mv.generate_variables(require_outputs=True)
    json.dumps(variables)
    assert isinstance(variables, dict)
