# for_your_eyes_only — ATAC Mission Software

**For Your Eyes Only (1981)** · mission codename **ATAC**

A deterministic, real-math implementation of the ATAC recovery-and-targeting
mission in the PROJECT BOND film suite. The lost targeting-communicator key is
escrowed across custodians and erasure-coded against loss, recovered from a
wreck underwater, reached via an Ionian insertion route, then directed onto a
moving target and uplinked acoustically.

## Mission concept modules

| Module | Concept | Mathematics |
|---|---|---|
| `src/for_your_eyes_only/key_escrow.py` | ATAC key escrow/recovery: custody, verification, release | Shamir secret sharing over GF(2⁶¹−1), share commitments, SHA-256 custody chain |
| `src/for_your_eyes_only/key_recovery.py` | Erasure-coded key recovery | Vandermonde / Reed–Solomon-style code over GF(p); any-`k`-of-`n` reconstruction + integrity checksum |
| `src/for_your_eyes_only/underwater_retrieval.py` | Underwater retrieval planning (depth/currents) | current-drift compensation, Haldane-style multi-compartment decompression |
| `src/for_your_eyes_only/island_routing.py` | Greek-island insertion routing | weighted graph, Dijkstra / A* shortest path with risk cost |
| `src/for_your_eyes_only/targeting.py` | Fire-control targeting | constant-bearing intercept (quadratic), lead angle, closest-approach fallback |
| `src/for_your_eyes_only/acoustic_link.py` | Underwater acoustic link | Thorp absorption, geometric+absorption loss, SNR link budget, bisection max range |

Each domain module is **pure and infrastructure-free** — importable without
`bond-api`. The thin adapter `src/for_your_eyes_only/mission.py` implements the
**frozen** `bond_api.MissionProvider` protocol and registers the suite's
gadgets with `bond_api.GadgetRegistry`, so the orchestrator discovers and
drives ATAC like any other film. A single canonical scenario
(`mission.canonical_mission`) feeds both the mission outcome and the manuscript
variables, so the two can never disagree.

## Layout

```
src/for_your_eyes_only/   pure domain core (6 modules) + mission adapter + figures
scripts/                  thin per-phase CLIs (brief/recon/plan/execute/debrief)
tests/                    real-data, mock-free test suite per module
manuscript/               config + prose sections (tokens injected from code)
output/                   regenerable artifacts (figures, resolved manuscript) — gitignored
```

## Mission phases

```bash
uv run python scripts/brief.py
uv run python scripts/recon.py
uv run python scripts/plan.py
uv run python scripts/execute.py
uv run python scripts/debrief.py
uv run python scripts/00_preflight.py     # end-to-end verdicts
uv run python scripts/z_generate_manuscript_variables.py   # tokens + figures
```

## Protocol integration

Consumes the frozen `bond-api` protocol via a local path dependency:

```toml
[tool.uv.sources]
bond-api = { path = "/Users/4d/Documents/GitHub/template/projects/working/bond/bond-api" }
```

`mission.py` exposes `MissionProvider` at module top level under a stable name;
the orchestrator's `load_provider("for_your_eyes_only")` discovers it on
`sys.path`. The public protocol surface (brief/recon/plan/execute/debrief and
the module-level `GADGETS` registry) is stable across build phases; only the
internal scenario deepens.

## Verification

```bash
uv run python -m pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/
uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
```

Deterministic: fixed seeds, no mocks, no wall-clock dependence in persisted
artifacts. This is a **local-only** tree — never push.

## License

MIT © 2026 Daniel Ari Friedman (Active Inference Institute).
