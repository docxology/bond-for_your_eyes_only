# TODO — for_your_eyes_only (ATAC)

PROJECT BOND film package **For Your Eyes Only / ATAC**. Local-only tree;
scope is exactly this directory.

## Phase-4 deep-improvement build (current)

Added three new real-math domain modules and deepened the mission in place,
keeping the public protocol surface (brief/recon/plan/execute/debrief +
module-level `GADGETS`) unchanged:

- [x] **Fire-control targeting** (`src/for_your_eyes_only/targeting.py`)
      — constant-bearing intercept solved as a quadratic; returns intercept
      time, lead angle, weapon course, feasibility, and closest-approach
      fallback when a close is impossible.
- [x] **Erasure-coded key recovery** (`src/for_your_eyes_only/key_recovery.py`)
      — Vandermonde/Reed–Solomon-style code over GF(p); any-`k`-of-`n`
      reconstruction, integrity checksum that detects corrupted fragments.
- [x] **Underwater acoustic link budget**
      (`src/for_your_eyes_only/acoustic_link.py`) — Thorp absorption,
      geometric+absorption transmission loss, SNR = SL − TL − NL + DI, and a
      deterministic bisection for the maximum closure range.
- [x] **`canonical_mission()` single source of truth** in `mission.py` — the
      mission outcome and the manuscript `{{TOKEN}}`s both draw from one
      deterministic scenario, so they can never disagree.
- [x] **Mission deepened** — plan now sequences six steps and execute produces
      six result blocks (escrow, key recovery, retrieval, routing, targeting,
      acoustic link), with deterministic provenance.
- [x] **Figures** — added `targeting_geometry.png` and `acoustic_link.png`
      (four total: + island_graph, dive_profile).
- [x] **Manuscript** — methodology/results/conclusion updated with the new
      concepts; config keywords extended; references.bib adds Reed & Solomon,
      Thorp, and Urick.
- [x] **Gates** — `pytest --cov=src --cov-fail-under=90` (~95.5%), ruff check +
      format, mypy, zero `template[_]code_project` lineage, no mocks.

## Done (phase-2 build)

- Escrow/recovery core (`key_escrow.py`) — Shamir split/recover, commitments,
  custody chain, quorum release.
- Underwater retrieval core (`underwater_retrieval.py`) — Haldane model,
  decompression, current-drift compensation.
- Island routing core (`island_routing.py`) — weighted graph, Dijkstra/A*.
- Mission adapter + thin per-phase CLIs + manuscript variables + figures.
- Config/metadata (CITATION.cff, .zenodo.json, codemeta.json) for ATAC.

## Declared integration points (not yet bound)

- [ ] **Shared provenance persistence** — outcomes currently carry
      `Provenance` in memory only. When `bond_utilities.mission_io` ships,
      bind `execute()` to persist provenance via
      `record_provenance_outcome(mission_id, seed, version, input_payload, …)`.
      Acceptance: a persisted record whose `provenance.input_hash` matches the
      in-memory hash.
- [ ] **Orchestrator auto-discovery** — discovery verified against
      `bond_api.load_provider("for_your_eyes_only")`; confirm the coordinator
      picks ATAC up without explicit slug listing once fleet discovery is wired.

## Notes

- Pure domain modules intentionally have **no** `bond_api` import; `mission.py`
  is the only adapter. `canonical_mission()` lives in `mission.py` and is the
  shared scenario driver.
- Figures/output are gitignored (regenerable); regenerating the tree is
  byte-identical, a live determinism proof.
