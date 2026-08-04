# for_your_eyes_only — ATAC Mission Software

**For Your Eyes Only (1981)** · mission codename **ATAC**

A deterministic, real-math implementation of the ATAC recovery mission in the
PROJECT BOND film suite. The lost targeting-communicator key is escrowed
across custodians, recovered from a wreck underwater, and reached via an
Ionian insertion route.

## Mission concepts

| Module | Concept | Mathematics |
|---|---|---|
| `src/for_your_eyes_only/key_escrow.py` | ATAC lost-key escrow/recovery: custody, verification, release | Shamir secret sharing over GF(2⁶¹−1), share commitments, SHA-256 custody chain |
| `src/for_your_eyes_only/underwater_retrieval.py` | Underwater retrieval planning (depth/currents) | current-drift compensation, Haldane-style multi-compartment decompression |
| `src/for_your_eyes_only/island_routing.py` | Greek-island insertion routing | weighted graph, Dijkstra / A* shortest path with risk cost |

Each domain module is **pure and infrastructure-free** — importable without
`bond-api`. The thin adapter `src/for_your_eyes_only/mission.py` implements the
**frozen** `bond_api.MissionProvider` protocol and registers the suite's
gadgets with `bond_api.GadgetRegistry`, so the orchestrator discovers and
drives ATAC like any other film.

## Layout

```
src/for_your_eyes_only/   pure domain core + mission adapter + figures
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
`sys.path`.

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
