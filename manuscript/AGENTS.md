# Manuscript rules — for_your_eyes_only (ATAC)

Rules for editing the ATAC manuscript. Syntax reference:
[`SYNTAX.md`](SYNTAX.md). Directory guide: [`README.md`](README.md).

## The one rule that matters

**Never type a metric into prose.** Every quantitative claim arrives as a token
substituted from `src/for_your_eyes_only/manuscript_variables.py`, which
computes it from `mission.canonical_mission()`.

This is not stylistic. A number typed into a section is a copy that stops
tracking the code the moment the code changes, and it fails silently — the
manuscript keeps rendering, keeps looking authoritative, and is wrong. A token
cannot do that: if the value moves, the rendered text moves with it.

To add a quantitative result:

1. Put the value on `CanonicalMission` if it is not already there.
2. Add a `RESULT_*` entry to `_compute_mission_metrics()`, formatted as a
   string.
3. Reference the token in prose.
4. `uv run pytest tests/test_manuscript_variables.py`.

## What the gates enforce

`tests/test_manuscript_variables.py`:

- every token appearing in a numbered section must exist in
  `generate_variables()`;
- rendering must leave no unsubstituted placeholder in any section.

The fleet-level docs gate additionally scans `00_abstract.md`, `03_results.md`,
and `04_conclusion.md` for hand-authored metric patterns — percentages, test
counts, coverage figures.

Because numbered sections are scanned, you cannot write a literal token in a
sentence *about* tokens; describe it in words and put the example in
`SYNTAX.md`, which is excluded for exactly that reason.

## Test counts and coverage

Do not quote them. State the gate instead —
`pytest tests/ --cov=src --cov-fail-under=90` — and let the command report the
measurement. A percentage in prose is a snapshot with an expiry date nobody
tracks.

## References

`references.bib` and `99_references.md` must stay consistent, and every entry
must be a real publication with real authors, a real title, and a real year.

If you are not confident a reference exists as you have written it, **remove
it**. A fabricated citation is worse than a missing one: it is unfalsifiable to
a casual reader and corrodes trust in the entries that are genuine. Where a
technique is standard textbook material with no single canonical paper, say so
explicitly — as the fire-control section does — rather than attaching a
plausible-looking citation.

## Section set

The canonical set is fixed: `00_abstract`, `01_introduction`, `02_methodology`,
`03_results`, `04_conclusion`, `05_experimental_setup`, `06_reproducibility`,
`07_scope_and_related_work`, `99_references`. Sidecars are `README.md`,
`AGENTS.md`, `SYNTAX.md`, `config.yaml`, `preamble.md`, `references.bib`.

Keep each section doing its own job: methodology explains the mathematics,
results reports what the code computed, experimental setup states the
configuration, reproducibility states the determinism contract, and scope names
the limits honestly.

## `config.yaml`

Metadata (title, subtitle, keywords) feeds `BOND_*` and `CONFIG_*` tokens and
must describe what the package actually does.

The `mission:` block is a **checked mirror**, not an input. No manuscript number
comes from it; every one is computed from the constants in `mission.py`. It is
pinned to those constants by `tests/test_config_consistency.py`. Change a
mission constant and you must change the block — the test will say so. Never
add a value to the block that no code reads: that is how it previously came to
declare an escrow key of 4242 that nothing used.

## Figures

Generators live in `src/for_your_eyes_only/figures.py` and render
deterministically to `output/figures/`. Every figure referenced in prose must
have a generator, and every generator's output should be referenced. Regenerate
with `uv run python scripts/z_generate_manuscript_variables.py`.

## Honesty in scope

`07_scope_and_related_work.md` states the limitations plainly: stylised graph
geometry, classroom-grade decompression and absorption models, not certified
for live operations. Keep it that way. If a new module carries a simplification
a reader could mistake for a validated model, name the simplification there.
