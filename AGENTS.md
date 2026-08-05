# for_your_eyes_only — ATAC Mission Software

This is a PROJECT BOND film package. Scope is **exactly this directory**.
It is a **local-only** working tree: no remote, never push.
All builds/tests run from this directory.

## Mission

Film: **For Your Eyes Only (1981)** · mission codename **ATAC**.

The ATAC (Automatic Targeting Attack Communicator) is a lost-key targeting
device whose recovery and employment span custody, underwater access, routing,
fire control, and acoustic communications. The mission software must: escrow
its key across custodians (no single holder may release it) and erasure-code
it against loss; recover the device from a wreck underwater (compensating for
depth and currents); route the insertion across the Greek islands; then direct
it onto a moving contact and uplink targeting data acoustically.

## Architecture & layer contract

| Surface | Rule |
|---|---|
| `src/for_your_eyes_only/key_escrow.py`, `key_recovery.py`, `underwater_retrieval.py`, `island_routing.py`, `targeting.py`, `acoustic_link.py` | Pure domain mathematics — **no** `infrastructure.*`, no `bond_api` imports; importable standalone |
| `src/for_your_eyes_only/mission.py` | Thin adapter implementing the **frozen** `bond_api.MissionProvider` + `GadgetRegistry` + `canonical_mission()` single source of truth |
| `scripts/` | Thin per-phase orchestrators (business logic stays in `src/`) |
| `src/for_your_eyes_only/figures.py` | Deterministic matplotlib figure generation (Agg backend) |
| manuscript tokens | Injected from `manuscript/config.yaml` + `src/.../manuscript_variables.py` + `canonical_mission()`; never hand-authored metrics |

## Hard guardrails

- **Scope exactly this package** — never touch siblings, bond-root files, or
  the template repo.
- **No mocks** — real data + computation only; zero `MagicMock`/`unittest.mock`.
- **≥90% line+branch on `src/`** — `uv run python -m pytest tests/ --cov=src --cov-fail-under=90`.
- **Deterministic** — fixed seeds, no untracked RNG, no wall-clock in artifacts.
- **Thin scripts** — logic lives in `src/`.
- **ruff + mypy clean** on `src/` and `scripts/`.

## Protocol integration

The frozen `bond-api` protocol is a local path dependency
(`[tool.uv.sources] bond-api = { path = ".../bond-api" }`). `mission.py`
exposes `MissionProvider` at module top level under a stable name so the
orchestrator's `load_provider("for_your_eyes_only")` discovers it. The public
protocol surface and the module-level `GADGETS` convention are stable across
phases — bond-cli, the coordinator reconcile, and the orchestrator consume them
unchanged; only the internal mission scenario deepens.

## Verification

```bash
uv run python -m pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/
uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
# lineage: no leftover template strings (verification-check descriptions only)
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**'
```

## Key files

- `src/for_your_eyes_only/key_escrow.py` — escrow/recovery protocol (Shamir).
- `src/for_your_eyes_only/key_recovery.py` — erasure-coded key recovery.
- `src/for_your_eyes_only/underwater_retrieval.py` — dive/drift planning.
- `src/for_your_eyes_only/island_routing.py` — Ionian insertion routing.
- `src/for_your_eyes_only/targeting.py` — fire-control intercept solution.
- `src/for_your_eyes_only/acoustic_link.py` — underwater acoustic link budget.
- `src/for_your_eyes_only/mission.py` — frozen-protocol provider + gadgets +
  canonical scenario.
- `manuscript/config.yaml` — mission + metadata configuration.
