# Manuscript (`projects/working/bond/for_your_eyes_only/manuscript/`)

This directory holds the ATAC mission manuscript. Numbered prose sections
(`NN_*.md`) may contain `{{TOKEN}}` placeholders resolved by
`src/for_your_eyes_only/manuscript_variables.py` at render time.

## Files

| File | Role |
|---|---|
| `config.yaml` | Paper metadata + mission parameters (source of variables) |
| `NN_*.md` | Numbered prose sections (00 abstract … 07 scope, 99 references) |
| `references.bib` | BibTeX bibliography |
| `preamble.md` | LaTeX preamble injections |

## Token protocol

* Numeric/result values **must** use `{{TOKEN}}` syntax, never hardcoded prose.
* The full token set is the return value of `generate_variables()`; the live
  cross-reference test `tests/test_manuscript_variables.py` fails if a prose
  token is undefined.
* Sidecar files that legitimately illustrate `{{TOKEN}}` syntax
  (this guide, SYNTAX.md, AGENTS.md) are excluded from the strict
  cross-reference scan.

## Figure protocol

Figures are referenced via Pandoc-crossref `[@fig:label]` / `{#fig:label}`
(see §3). Generators live in `src/for_your_eyes_only/figures.py` and render
deterministically to `output/figures/`.

## Reproduction

```bash
uv run python scripts/z_generate_manuscript_variables.py
# writes output/data/manuscript_variables.json, output/manuscript/, output/figures/
```
