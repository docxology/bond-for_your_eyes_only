# Reproducibility

## Determinism contract

* **Fixed RNG seed** — escrow share generation is the only stochastic step and
  it draws from a fixed seed ({{BOND_CODENAME}} seed {{RESULT_MISSION_SEED}});
  every other module is pure arithmetic. No untracked randomness anywhere.
* **No wall clock in artifacts** — provenance records a zero wall time; the
  only timestamp is an explicit, injectable generation stamp.
* **No mocks** — tests exercise real data and real computation only.
* **Gates** — the suite must pass `pytest --cov=src --cov-fail-under=90`,
  ruff, and mypy; the manuscript token cross-reference is itself a test.

## Artifact inventory

The generation orchestrator writes:

* `output/data/manuscript_variables.json` — the full token map.
* `output/manuscript/` — resolved manuscript sections (no raw braces).
* `output/figures/island_graph.png`, `output/figures/dive_profile.png`,
  `output/figures/targeting_geometry.png`, `output/figures/acoustic_link.png` —
  the deterministic figure set.

Regenerating the tree reproduces byte-identical, git-clean output, a live
proof of determinism.

## Test results

Test counts and coverage percentages are deliberately not quoted here. A number
typed into prose is a snapshot that decays silently on the next commit; the
*gate* is the durable claim, and it is stated instead:
`pytest tests/ --cov=src --cov-fail-under=90` must pass with zero failures and
zero skips. The measured figure is reported by that command, not by this
sentence.

The suite covers, per module: escrow split/recover round-trips, commitment
verification, quorum rejection and tamper rejection; erasure encode/recover
round-trips, exhaustive any-`k` recovery over every surviving-fragment
combination, and checksum corruption detection; underwater descent/ascent
scheduling, drift compensation, and reachability edges; routing optimality,
Dijkstra/A* agreement, risk sensitivity, disconnected-graph and unknown-node
errors; fire-control intercept feasibility, lead-angle geometry, and the
closest-approach fallback on both the equal-speed and negative-discriminant
branches; and acoustic-link path loss, SNR monotonicity, bisection closure, and
the non-closing case.

Two suites exist specifically to stop documentation drifting from code:

* `tests/test_config_consistency.py` pins every value declared in
  `manuscript/config.yaml`'s `mission:` block to the constant the mission
  actually runs with, so the config cannot decay into decoration.
* `tests/test_manuscript_variables.py` fails if any token used in prose is
  absent from `generate_variables()`, or if a rendered section still contains
  an unsubstituted placeholder. (The token syntax itself is documented in
  `manuscript/SYNTAX.md`, which is excluded from that scan precisely because it
  must show the raw form.)

See `tests/` and `docs/testing_philosophy.md`.
