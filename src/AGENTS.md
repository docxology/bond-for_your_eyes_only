# src/for_your_eyes_only — ATAC mission core

Pure, deterministic implementation of the ATAC recovery mission. This
directory is the **mathematical core**; the only module coupled to the BOND
protocol is `mission.py`.

## Layer contract

| Module | Responsibility | Imports |
|---|---|---|
| `key_escrow.py` | Escrow/recovery: key split, custody, verification, release (Shamir) | stdlib only |
| `underwater_retrieval.py` | Dive/drift planning: Haldane model, decompression, current offset | stdlib only |
| `island_routing.py` | Ionian insertion routing: weighted graph, Dijkstra/A* | stdlib only |
| `mission.py` | Frozen `bond_api.MissionProvider` + `GadgetRegistry` adapter | `bond_api` + domain modules |
| `manuscript_variables.py` | Token hydration for the manuscript | `yaml` + domain modules |
| `figures.py` | Deterministic matplotlib figure generation | `matplotlib` + domain modules |

Pure domain modules (`key_escrow`, `underwater_retrieval`, `island_routing`)
are **infrastructure-free and importable without `bond-api`** — add no
`infrastructure.*` or `bond_api` imports to them.

## Conventions

- Type hints + docstrings everywhere; ruff + mypy clean.
- Deterministic: fixed seeds, no untracked RNG, no wall-clock in artifacts.
- `mission.py` exposes `MissionProvider` at module top level under a stable
  name for orchestrator discovery; `GADGETS` holds the registered gadget map.
