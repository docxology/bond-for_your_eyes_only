# for_your_eyes_only — ATAC Mission Software

**For Your Eyes Only (1981)** · mission codename **ATAC**

A deterministic, real-mathematics implementation of the ATAC recovery-and-
targeting mission in the PROJECT BOND film suite.

## The film, and what it becomes in software

In the film, the ATAC — Automatic Targeting Attack Communicator — is lost with
the surveillance ship *St. Georges* and must be recovered from the wreck before
it falls into the wrong hands. Strip the plot away and a set of genuine
technical problems remains, which is what this package implements:

| Film concept | Software payload |
|---|---|
| A device too dangerous for any one person to control | Threshold key escrow: no single custodian can release the key |
| A key that must survive being lost at sea | Erasure coding: any `k` of `n` stored fragments reconstruct it |
| The wreck lies at depth under current | Dive planning with decompression scheduling and drift compensation |
| Reaching the site across the Ionian islands | Least-cost route planning over a distance-plus-risk cost |
| The device directs a weapon onto a moving contact | Constant-bearing fire-control intercept solution |
| It must report the solution from underwater | Underwater acoustic link budget and coverage radius |

## Modules

Six pure domain modules, one protocol adapter, plus rendering and manuscript
support.

| Module | Computes | Mathematics |
|---|---|---|
| `src/for_your_eyes_only/key_escrow.py` | ATAC key escrow: custody, verification, quorum release | Shamir secret sharing over GF(2⁶¹−1), `g^y` share commitments, SHA-256 custody chain |
| `src/for_your_eyes_only/key_recovery.py` | Erasure-coded key survival; any `k` of `n` fragments reconstruct | Systematic Reed–Solomon-style code over GF(p), Vandermonde solve, integrity checksum |
| `src/for_your_eyes_only/underwater_retrieval.py` | Dive profile, decompression limits, current-drift offset | Haldane multi-compartment tissue model, staged ascent, ballistic drift |
| `src/for_your_eyes_only/island_routing.py` | Least-cost Ionian insertion route (risk changes cost, not choice — see [`docs/architecture.md`](docs/architecture.md)) | Weighted graph, Dijkstra and A\* with a straight-line admissible heuristic |
| `src/for_your_eyes_only/targeting.py` | Fire-control firing solution against a moving contact | Constant-bearing intercept quadratic, lead angle, closest-approach fallback |
| `src/for_your_eyes_only/acoustic_link.py` | Uplink budget and coverage radius | Thorp absorption, spreading loss, `SNR = SL − TL − NL + DI`, bounded bisection |
| `src/for_your_eyes_only/mission.py` | The frozen-protocol adapter and canonical scenario | Implements `bond_api.MissionProvider`; owns `GADGETS` and `canonical_mission()` |
| `src/for_your_eyes_only/figures.py` | Four deterministic figures | matplotlib on the `Agg` backend |
| `src/for_your_eyes_only/manuscript_variables.py` | Manuscript token hydration | Derives every reported number from the canonical mission |

The six domain modules are **pure and infrastructure-free** — importable
without `bond-api`, and independent of each other except that `key_recovery`
reuses `key_escrow`'s prime field, so shares and fragments live in the same
GF(p).

## The MissionProvider surface

`mission.py` implements the frozen `bond_api.MissionProvider` protocol. This
shape is consumed by `bond-cli`, the coordinator, and the orchestrator across
package boundaries, and does not change:

```python
class MissionProvider:
    film: str                                                    # "for_your_eyes_only"
    def brief(self) -> MissionBrief: ...                         # objectives, escrow asset, constraints
    def recon(self, request: ReconRequest) -> ReconReport: ...   # findings
    def plan(self, brief: MissionBrief) -> MissionPlan: ...      # six ordered steps
    def execute(self, plan: MissionPlan) -> MissionOutcome: ...  # results + provenance
    def debrief(self, outcome: MissionOutcome) -> Debrief: ...   # outcome + lessons
```

Alongside it, a module-level `GADGETS: dict[str, object]` registry (built by
`build_gadgets()`) exposes the domain callables and prepared state the
orchestrator may invoke.

The plan sequences six steps — `escrow_release`, `key_recovery`,
`underwater_retrieval`, `island_routing`, `targeting`, `acoustic_link` — and
`execute()` returns a result block for each, plus deterministic `Provenance`
(package version, seed, input hash, zero wall time).

### One scenario, two consumers

`canonical_mission()` returns a frozen `CanonicalMission` holding one
deterministic run's typed outputs. Both `execute()` and the manuscript's token
hydration read from it, so the report and the mission outcome cannot disagree —
not because they are kept in sync, but because there is only one of them.

## Install and run

```bash
uv sync
```

Mission phases (each prints deterministic sorted JSON):

```bash
uv run python scripts/brief.py
uv run python scripts/recon.py "recover the lost ATAC device"
uv run python scripts/plan.py
uv run python scripts/execute.py
uv run python scripts/debrief.py
```

End-to-end verdicts, and artifact regeneration:

```bash
uv run python scripts/00_preflight.py                     # PASS/FAIL per verdict
uv run python scripts/z_generate_manuscript_variables.py  # tokens + resolved sections + figures
```

## Verification

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/
uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
```

Branch coverage is enabled and the floor is 90% of `src/`. Test counts and
coverage percentages are deliberately not quoted here — the gate above is the
durable claim, and the command prints today's measurement.

The suite uses **no mocking framework**: real field arithmetic, real temporary
files, real subprocess CLI runs, real PNG renders. Where a failure branch is
unreachable from real inputs, the code provides a real injectable seam rather
than a patched dependency. See [`docs/testing_philosophy.md`](docs/testing_philosophy.md).

## Layout

```
src/for_your_eyes_only/   six pure domain modules + mission adapter + figures + tokens
scripts/                  thin per-phase CLIs (brief/recon/plan/execute/debrief) + tools
tests/                    real-data, mock-free suite
manuscript/               config + tokenised prose sections + references
docs/                     architecture, agent rules, operational instructions, test doctrine
output/                   regenerable artifacts (figures, resolved manuscript) — gitignored
```

## Documentation

| Read | For |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Module-by-module internals and how the layers compose |
| [`docs/agent_instructions.md`](docs/agent_instructions.md) | Commands and task recipes |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Rules and invariants for changing this package |
| [`docs/testing_philosophy.md`](docs/testing_philosophy.md) | What counts as a test here |
| [`manuscript/`](manuscript/) | The scientific report on the ATAC mission |
| [`TODO.md`](TODO.md) | Remaining work and unbound integration points |

## Protocol integration

`bond-api` is consumed as a local path dependency:

```toml
[tool.uv.sources]
bond-api = { path = "/Users/4d/Documents/GitHub/template/projects/working/bond/bond-api" }
```

The orchestrator's `load_provider("for_your_eyes_only")` discovers
`MissionProvider` at module top level on `sys.path`.

## Provenance

Deterministic throughout: one fixed seed, no untracked randomness, no
wall-clock value in any persisted artifact — the one date in the tree is a
build stamp taken from `SOURCE_DATE_EPOCH` or the declared `paper.date`.
Regenerating `output/` reproduces it byte-for-byte, checked by
`tests/test_scripts_smoke.py::test_regenerating_the_artifact_tree_is_byte_identical`,
which runs the generator twice into two roots and diffs every file.

This is a **local-only** tree with no remote — never push.

## License

MIT © 2026 Daniel Ari Friedman (Active Inference Institute).
