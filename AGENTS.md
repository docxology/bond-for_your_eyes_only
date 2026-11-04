# for_your_eyes_only — ATAC Mission Software

PROJECT BOND film package for **For Your Eyes Only (1981)**, mission codename
**ATAC**. Scope is **exactly this directory**. The only permitted remote is
`origin` (`github.com/docxology/bond-for_your_eyes_only`) — never push to a
sibling package or the template repository. All commands run from this
directory.

Detailed guidance lives in `docs/`:

| Document | Covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Module-by-module internals, layer topology, protocol adapter |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Full working rules, invariants, and package-specific traps |
| [`docs/agent_instructions.md`](docs/agent_instructions.md) | Commands and task recipes |
| [`docs/testing_philosophy.md`](docs/testing_philosophy.md) | No-mock / real-data / determinism doctrine |

## Mission

The ATAC is a lost-key targeting device whose recovery and employment span
custody, underwater access, routing, fire control, and acoustic
communications. The software escrows its key across custodians so no single
holder may release it and erasure-codes it against loss; plans the wreck dive
against depth and current; routes the insertion across the Ionian islands;
computes a firing solution against a moving contact; and budgets the acoustic
uplink that carries the solution back.

## Build and test

```bash
uv sync --extra dev                                  # install (dev tools; bond-api is vendored)

uv run pytest tests/ --cov=src --cov-fail-under=90   # tests + branch coverage, floor 90% of src/
uv run ruff check src/ scripts/ tests/               # lint
uv run ruff format --check src/ scripts/ tests/      # formatting
uv run mypy src/ scripts/                            # types
```

Run the mission end to end:

```bash
uv run python scripts/00_preflight.py                # PASS/FAIL verdicts, non-zero exit on failure
uv run python scripts/brief.py                       # also: recon plan execute debrief
uv run python scripts/z_generate_manuscript_variables.py   # tokens + resolved manuscript + figures
```

## Architecture contract

| Surface | Rule |
|---|---|
| `src/for_your_eyes_only/{key_escrow,key_recovery,underwater_retrieval,island_routing,targeting,acoustic_link}.py` | Pure domain mathematics — no `infrastructure.*`, no `bond_api`; importable standalone |
| `src/for_your_eyes_only/mission.py` | The only adapter: frozen `bond_api.MissionProvider` + `GADGETS` + `canonical_mission()` single source of truth |
| `src/for_your_eyes_only/figures.py` | Deterministic matplotlib rendering (`Agg` backend) |
| `src/for_your_eyes_only/manuscript_variables.py` | Token hydration; `METRIC_TOKENS` derived, never hand-listed |
| `scripts/` | Thin orchestrators — argument handling, imports, output formatting; no business logic |
| `manuscript/` | Tokenised prose; metrics injected from code, never hand-authored |

## Hard guardrails

- **Scope exactly this package** — never touch siblings, bond-root files, or
  the template repo.
- **Frozen protocol** — `brief`/`recon`/`plan`/`execute`/`debrief` and the
  module-level `GADGETS` registry keep their public shape. Deepen inside;
  never break discovery.
- **No mocks** — no `MagicMock`, `unittest.mock`, or `mocker.patch`. Real data
  and real computation; use a real injectable seam when a failure path needs
  driving.
- **≥90% line+branch on `src/`**, zero failures, zero skips.
- **Deterministic** — one fixed seed (`mission.MISSION_SEED`), no untracked
  RNG, no wall-clock value in any persisted artifact.
- **Thin scripts** — computation lives in `src/`.
- **ruff + mypy clean** on `src/` and `scripts/`.
- **No hand-authored metrics** — every manuscript number is a token computed
  from `canonical_mission()`.

## Package-specific traps

- **`canonical_mission()` is the single source of truth.** Computing a mission
  quantity anywhere else creates a second source that can disagree. Add a field
  to `CanonicalMission` instead.
- **Verdicts must be derivable.** `fingerprint_match` is recomputed and
  compared, not stapled to `True`, because `00_preflight.py` reads it as a
  pass/fail verdict. Before adding a boolean, ask what input would make it
  False; if there is no answer, it is not a check.
- **`manuscript/config.yaml`'s `mission:` block is a mirror, not an input.** It
  is pinned to the `mission.py` constants by `tests/test_config_consistency.py`.
  Change a constant, change the block. Never add a value nothing reads.
- **The erasure decoder's generality is the feature.** `recover_erasure` takes
  an explicit surviving-fragment `indices` set; the exhaustive combination test
  is what makes the any-`k` claim real. Keep it.
- **`__all__` is hand-maintained** — add new public functions to it.

## Verification checklist

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
uv run python scripts/00_preflight.py

# lineage: exemplar identifiers only permitted in prose that explains the lineage
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**'
# no-mock policy
rg -n "MagicMock|unittest\.mock|mocker\.patch" tests/

git status   # must be clean after committing
```

Report the coverage percentage and test count you actually observed, the commit
SHA, and anything you could not verify. A gate you did not run is not a gate
that passed.

## Key files

- `src/for_your_eyes_only/key_escrow.py` — Shamir escrow, commitments, custody chain, quorum release.
- `src/for_your_eyes_only/key_recovery.py` — erasure-coded any-`k`-of-`n` key recovery.
- `src/for_your_eyes_only/underwater_retrieval.py` — Haldane dive/decompression and drift planning.
- `src/for_your_eyes_only/island_routing.py` — Ionian insertion routing (Dijkstra / A\*).
- `src/for_your_eyes_only/targeting.py` — fire-control intercept solution.
- `src/for_your_eyes_only/acoustic_link.py` — underwater acoustic link budget.
- `src/for_your_eyes_only/mission.py` — frozen-protocol provider, gadgets, canonical scenario.
- `manuscript/config.yaml` — paper metadata plus the checked mission mirror.
