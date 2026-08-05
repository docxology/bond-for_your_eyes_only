# Manuscript syntax — for_your_eyes_only (ATAC)

The markup conventions used by the ATAC manuscript sections.

> This file is **excluded** from the strict token scan (it matches no
> `NN_*.md` glob), which is exactly why it can show raw token syntax below.
> Numbered prose sections cannot: an unresolved placeholder there is an error.

## Tokens

Every metric is written as a double-brace token and substituted at render time
from `src/for_your_eyes_only/manuscript_variables.py`:

```markdown
The reconstructed key is {{RESULT_ESCROW_KEY}}, matching the escrow
fingerprint ({{RESULT_RECOVERED_MATCH}}).
```

Token names are `[A-Z0-9_]+` between double braces. There are three families:

| Prefix | Source | Examples |
|---|---|---|
| `RESULT_*` | computed live from `mission.canonical_mission()` | `RESULT_ROUTE`, `RESULT_FIRE_LEAD_DEG`, `RESULT_LINK_MARGIN_DB` |
| `BOND_*` / `CONFIG_*` | `manuscript/config.yaml` metadata | `BOND_TITLE`, `BOND_CODENAME`, `CONFIG_KEYWORDS` |
| environment | the render environment | `PYTHON_VERSION`, `SOURCE_DATE` |

**The rule: never type a number.** If a value is not yet a token, add it to
`_compute_mission_metrics()` first. `tests/test_manuscript_variables.py` fails
on a prose token with no generator, and `resolve_manuscript_tree` fails in
strict mode if any placeholder survives rendering.

Writing a literal token in a sentence *about* tokens will therefore break a
numbered section — describe the syntax in words there, and put the example
here.

## Figures

Pandoc-crossref syntax. Define with `{#fig:label}` on the image, reference with
`[@fig:label]` — square brackets, the same citation form as a bibliography key.
This guide previously specified the brace form, which pandoc-crossref does not
recognise; four references in §3 were written that way and would have rendered
as literal braces. `tests/test_manuscript_crossrefs.py` now rejects the brace
form in the sections *and* in this guide.

```markdown
The depth-time profile is shown in Figure [@fig:dive_profile].

![ATAC underwater retrieval dive profile](dive_profile.png){#fig:dive_profile}
```

Paths are bare filenames — figures resolve relative to `output/figures/`.

| Label | File | Generator in `figures.py` |
|---|---|---|
| `fig:island_graph` | `island_graph.png` | `render_island_graph` |
| `fig:dive_profile` | `dive_profile.png` | `render_dive_profile` |
| `fig:targeting_geometry` | `targeting_geometry.png` | `render_targeting_geometry` |
| `fig:acoustic_link` | `acoustic_link.png` | `render_acoustic_link` |

## Mathematics

LaTeX via `$...$` inline and `$$...$$` display. `amsmath` and `amssymb` are
loaded in `preamble.md`.

```markdown
The intercept satisfies $|p_0 + v_t t| = v_w t$, giving

$$(|v_t|^2 - v_w^2) t^2 + 2(p_0 \cdot v_t) t + |p_0|^2 = 0.$$
```

Note the interaction with tokens: `$n = ${{RESULT_ESCROW_SHARES}}` closes the
math span *before* the token so the substituted digits render as body text.

## Citations

BibTeX keys from `references.bib`, cited as `[@shamir1979share]`. Every entry
must be a real, checkable publication — real authors, real title, real year.
A reference you cannot verify should be removed, not shipped.

Current keys: `shamir1979share`, `reed1960polynomial`, `boycott1908prevention`,
`dijkstra1959note`, `hart1968formal`, `thorp1967analytic`, `urick1983principles`,
`buhlmann1984decompression`, `berlekamp1968algebraic`, `blakley1979safeguarding`.

## Section order

`00_abstract`, `01_introduction`, `02_methodology`, `03_results`,
`04_conclusion`, `05_experimental_setup`, `06_reproducibility`,
`07_scope_and_related_work`, `99_references`.

Only files matching `[0-9][0-9]_*.md` are rendered and token-scanned. This
file, `README.md`, and `AGENTS.md` are sidecars.
