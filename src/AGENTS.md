# src/for_your_eyes_only — ATAC mission core

Pure, deterministic implementation of the ATAC recovery-and-targeting mission.
This directory is the **mathematical core**; the only module coupled to the
BOND protocol is `mission.py`.

## Layer contract

| Module | Responsibility | Imports |
|---|---|---|
| `key_escrow.py` | Escrow/recovery: key split, custody, verification, release (Shamir) | stdlib only |
| `key_recovery.py` | Erasure-coded key recovery over GF(p) (Vandermonde/RS) | stdlib + `key_escrow` |
| `underwater_retrieval.py` | Dive/drift planning: Haldane model, decompression, current offset | stdlib only |
| `island_routing.py` | Ionian insertion routing: weighted graph, Dijkstra/A* | stdlib only |
| `targeting.py` | Fire-control intercept: lead angle, intercept time, closest approach | stdlib only |
| `acoustic_link.py` | Underwater acoustic link budget (Thorp, SNR, max range) | stdlib only |
| `mission.py` | Frozen `bond_api.MissionProvider` + `GadgetRegistry` + `canonical_mission()` | `bond_api` + domain modules |
| `manuscript_variables.py` | Token hydration for the manuscript | `yaml` + `mission` |
| `figures.py` | Deterministic matplotlib figure generation | `matplotlib` + domain modules |

Pure domain modules (`key_escrow`, `key_recovery`, `underwater_retrieval`,
`island_routing`, `targeting`, `acoustic_link`) are **infrastructure-free and
importable without `bond-api`** — add no `infrastructure.*` or `bond_api`
imports to them.

## Conventions

- Type hints + docstrings everywhere; ruff + mypy clean.
- Deterministic: fixed seeds, no untracked RNG, no wall-clock in artifacts.
- `mission.py` exposes `MissionProvider` at module top level under a stable
  name for orchestrator discovery; `GADGETS` holds the registered gadget map.
- `canonical_mission()` is the single source of truth for mission outcomes and
  manuscript tokens — never compute the same number twice in different places.
