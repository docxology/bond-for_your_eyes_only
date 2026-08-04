# TODO — for_your_eyes_only (ATAC)

Phase-2 build of the PROJECT BOND film package **For Your Eyes Only / ATAC**.
Local-only tree; scope is exactly this directory.

## Done (phase 2 build)

- [x] **Escrow/recovery core** (`src/for_your_eyes_only/key_escrow.py`)
      — Shamir secret sharing over GF(2⁶¹−1) with `split_key`/`recover_key`,
      per-share commitments (`commit_share`/`verify_share`), a SHA-256
      custody chain (`custody_chain_hash`, `generate_custody_transfer`), and
      high-level `create_escrow`/`release_key` with quorum + tamper gates.
- [x] **Underwater retrieval core** (`src/for_your_eyes_only/underwater_retrieval.py`)
      — Haldane-style `HaldaneModel` + `tissue_saturation`,
      `no_decompression_limit` (surface M-value), `plan_descent` staged
      ascent, `current_offset` drift compensation, `RetrievalPlanner`.
- [x] **Island routing core** (`src/for_your_eyes_only/island_routing.py`)
      — weighted `IslandGraph`, `build_ionian_graph`, Dijkstra/A*
      `plan_route` with distance+risk cost.
- [x] **Mission adapter** (`src/for_your_eyes_only/mission.py`) — implements
      the frozen `bond_api.MissionProvider` (brief/recon/plan/execute/debrief)
      and exposes `GADGETS` for `bond_api.GadgetRegistry`.
- [x] **Figures** (`src/for_your_eyes_only/figures.py`) — deterministic
      `island_graph.png` and `dive_profile.png`.
- [x] **Manuscript variables** (`src/for_your_eyes_only/manuscript_variables.py`)
      — token hydration from `manuscript/config.yaml` + computed metrics;
      strict-mode gate; live token cross-reference test.
- [x] **Thin CLIs** (`scripts/`) — brief/recon/plan/execute/debrief,
      `00_preflight.py`, `z_generate_manuscript_variables.py`.
- [x] **Config/metadata** — `manuscript/config.yaml`, CITATION.cff,
      .zenodo.json, codemeta.json rewritten for the ATAC package (no DOI —
      local-only).
- [x] **Gates** — `pytest --cov=src --cov-fail-under=90` (~95%), ruff check +
      format, mypy clean, zero `template[_]code_project` lineage strings, no mocks.

## Declared integration points (not yet bound)

- [ ] **Shared provenance persistence** — outcomes currently carry
      `Provenance` in memory only. When `bond_utilities.mission_io` ships,
      bind `execute()` to persist provenance via
      `record_provenance_outcome(mission_id, seed, version, input_payload, …)`
      so the orchestrator can audit outcomes on disk. Acceptance: a persisted
      record whose `provenance.input_hash` matches the in-memory hash.
- [ ] **Orchestrator auto-discovery** — discovery is verified against
      `bond_api.load_provider("for_your_eyes_only")`. When the suite
      coordinator wires fleet discovery, confirm ATAC is picked up without
      explicit slug listing.

## Notes

- Pure domain modules intentionally have **no** `bond_api` import — they stay
  importable if the path dep ever fails; `mission.py` is the only adapter.
- Figures/output are gitignored (regenerable); regenerating the tree is
  byte-identical, a live determinism proof.
