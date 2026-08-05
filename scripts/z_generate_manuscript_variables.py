"""Generate manuscript variables + figures for ATAC (thin orchestrator).

Writes ``output/data/manuscript_variables.json``, resolves the manuscript
tree to ``output/manuscript/``, and renders the figure set to
``output/figures/``. Strict by default: passes ``--allow-draft`` only for
early drafts that may fall back to "N/A" result tokens.

``--output-root DIR`` redirects the whole artifact tree elsewhere. That is what
makes the determinism claim testable end to end rather than by inspection:
``tests/test_scripts_smoke.py`` runs this script twice into two different roots
and compares every byte of the two trees.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PACKAGE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    allow_draft = "--allow-draft" in args
    require_outputs = not allow_draft
    output_root = _PACKAGE_ROOT / "output"
    if "--output-root" in args:
        output_root = Path(args[args.index("--output-root") + 1]).resolve()

    from for_your_eyes_only import figures, manuscript_variables

    variables = manuscript_variables.generate_variables(require_outputs=require_outputs)
    out_dir = output_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manuscript_variables.json").write_text(
        json.dumps(variables, sort_keys=True, indent=2), encoding="utf-8"
    )
    manuscript_variables.resolve_manuscript_tree(variables, strict=True, output_dir=output_root / "manuscript")
    rendered = figures.render_all(figure_dir=output_root / "figures")
    print(f"wrote {len(variables)} tokens -> {out_dir / 'manuscript_variables.json'}")
    print(f"figure paths: {[str(p) for p in rendered]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
