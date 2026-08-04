# Reproducibility

## Determinism contract

* **Fixed RNG seed** — the escrow and cable/route planning use a fixed seed
  ({{BOND_CODENAME}} seed 7); no untracked randomness.
* **No wall clock in artifacts** — provenance records a zero wall time; the
  only timestamp is an explicit, injectable generation stamp.
* **No mocks** — tests exercise real data and real computation only.
* **Gates** — the suite must pass `pytest --cov=src --cov-fail-under=90`,
  ruff, and mypy; the manuscript token cross-reference is itself a test.

## Artifact inventory

The generation orchestrator writes:

* `output/data/manuscript_variables.json` — the full token map.
* `output/manuscript/` — resolved manuscript sections (no raw braces).
* `output/figures/island_graph.png`, `output/figures/dive_profile.png` —
  deterministic figure set.

Regenerating the tree reproduces byte-identical, git-clean output, a live
proof of determinism.

## Test results

The suite covers, per module: escrow split/recover round-trips, commitment
verification, quorum rejection and tamper rejection; underwater descent/ascent
scheduling, drift compensation, reachability edges; and routing optimality,
risk sensitivity, and unknown-node errors. See `tests/`.
