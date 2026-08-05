# Operational instructions — for_your_eyes_only (ATAC)

Concrete commands and task recipes. For the rules behind them see
[`AGENTS.md`](AGENTS.md); for what the code does see
[`architecture.md`](architecture.md).

All commands run from the package root:
`projects/working/bond/for_your_eyes_only/`.

## Setup

```bash
uv sync
```

`bond-api` is a local path dependency declared in `pyproject.toml` under
`[tool.uv.sources]`. If it fails to resolve, the sibling `bond-api` package is
missing from the expected location — that is an environment problem, not a code
problem, and the six domain modules still import and test without it.

## The gates

Run all three before claiming anything works.

```bash
# 1. tests + coverage (must pass, must stay >= 90% on src/)
uv run pytest tests/ --cov=src --cov-fail-under=90

# 2. lint + formatting
uv run ruff check src/ scripts/ tests/
uv run ruff format --check src/ scripts/ tests/

# 3. types
uv run mypy src/ scripts/
```

Read the output. `--cov-fail-under` passing tells you the floor held; the
printed percentage is the measurement. A command you did not run is not a
command that passed.

## Running the mission

```bash
uv run python scripts/brief.py       # objectives, escrow asset, constraints
uv run python scripts/recon.py "recover the lost ATAC device"
uv run python scripts/plan.py        # the six ordered steps
uv run python scripts/execute.py     # results per step + provenance
uv run python scripts/debrief.py     # outcome + lessons
```

Each prints deterministic sorted JSON. The phase is taken from the script's own
filename, so a copy of one of these under a name that is not a protocol stage
exits 2 with `unknown phase`.

```bash
uv run python scripts/00_preflight.py
```

Prints a `[PASS]`/`[FAIL]` line per verdict and exits non-zero if any fails.
This is the fastest end-to-end check that the package is intact.

## Regenerating artifacts

```bash
uv run python scripts/z_generate_manuscript_variables.py
```

Writes `output/data/manuscript_variables.json`, resolves every numbered
manuscript section into `output/manuscript/` with tokens substituted, and
renders the four figures into `output/figures/`. Strict by default: an
unresolved placeholder is an error. Pass `--allow-draft` only when you
deliberately want `N/A` fallbacks.

`output/` is regenerable and gitignored. Never hand-edit anything in it, and
never edit it to make a check pass.

## Task recipes

### Adding a domain module

1. Write `src/for_your_eyes_only/<name>.py`: pure functions and frozen
   dataclasses, full type hints, a module docstring naming the real model and
   its source, no `bond_api` import, no RNG that is not seeded.
2. Add it to `__all__` and to the package docstring in `__init__.py`.
3. Write `tests/test_<name>.py` — round-trip, edge, and error paths.
4. If the mission should use it, add a field to `CanonicalMission`, compute it
   in `canonical_mission()`, add a `Step` in `plan()`, and add a result block in
   `execute()`. Do **not** change the five method signatures.
5. If it should be orchestrator-visible, add an entry to `build_gadgets()`.
6. Document it in `docs/architecture.md`, `../README.md`, and the manuscript
   methodology.

### Adding a result to the manuscript

Never type the number.

1. Make sure the value is on `CanonicalMission` (add a field if not).
2. Add a `RESULT_*` entry to `_compute_mission_metrics()` in
   `manuscript_variables.py`, formatted as a string.
3. Reference it in prose as a double-brace token.
4. Run `uv run pytest tests/test_manuscript_variables.py` — it fails if a prose
   token has no generator, and again if a rendered section still contains a
   placeholder.

`METRIC_TOKENS` is derived from the metric map, so the draft-mode fallback
updates itself. You do not maintain a second list.

### Changing a mission constant

Mission constants live in `mission.py` and are mirrored in
`manuscript/config.yaml`. Change both. `tests/test_config_consistency.py` fails
if you change only one — that is the point of it.

### Investigating a failure

Reproduce before theorising:

```bash
uv run pytest tests/test_<module>.py -v          # the failing module
uv run pytest tests/ -q -x                       # first failure, whole suite
uv run python scripts/00_preflight.py            # is the mission itself intact?
```

## Before you say you are done

- [ ] All three gates run, and you read the output
- [ ] Coverage at or above 90% on `src/`, zero failures, zero skips
- [ ] `rg -n "template_code_project" . --glob '!uv.lock' --glob '!.git/**'` —
      only lineage-explaining prose in docs may match
- [ ] `rg -n "MagicMock|unittest\.mock|mocker\.patch" tests/` — no matches
- [ ] `git status` clean after committing
- [ ] `../README.md`, `../AGENTS.md`, `../TODO.md` reflect what is now true
- [ ] Any number you report came from output you actually read
