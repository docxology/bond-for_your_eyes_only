# TODO — for_your_eyes_only (ATAC)

PROJECT BOND film package **For Your Eyes Only / ATAC**. Local-only tree; scope
is exactly this directory.

Completed build history is not tracked here — `git log` is the record. This
file lists only work that is genuinely still open, each item with the evidence
that it is open and the condition that would close it.

## Open — integration points not yet bound

Blocked on sibling packages, not on this one.

- [ ] **Persist provenance through `bond-utilities`.** `execute()` returns a
      `Provenance` (package version, seed, input hash, zero wall time) that
      exists in memory only. When `bond_utilities.mission_io` ships, bind
      `execute()` to `record_provenance_outcome(mission_id, seed, version,
      input_payload, ...)`.
      *Closes when:* a test reads a persisted record back off disk and asserts
      its `provenance.input_hash` equals the in-memory hash for the same run.

- [ ] **Confirm fleet auto-discovery.** Discovery is currently verified only
      against a direct `bond_api.load_provider("for_your_eyes_only")`.
      *Closes when:* the coordinator's reconcile step lists ATAC without the
      slug appearing anywhere in coordinator configuration.

## Open — package work

- [ ] **Wire the decompression ceiling into ascent staging.**
      `HaldaneModel.ceiling_m` and `no_decompression_limit` are implemented and
      tested, but `plan_descent` stages the ascent purely geometrically — fixed
      `STOP_INTERVAL` steps at fixed `ASCENT_RATE`, with no tissue-state
      consultation. The docstring, the module warning, and
      `manuscript/02_methodology.md` now say so explicitly rather than
      overclaiming, so this is a known limitation and not a hidden one.
      *Closes when:* stop depths and durations are derived from compartment
      ceilings, and a test shows a deeper or longer bottom time producing more
      or longer stops.

- [ ] **Drive the custody chain through the mission, or drop it.**
      `key_escrow` implements `generate_custody_transfer` and
      `custody_chain_hash`, and `EscrowState` carries a `custody_chain` field —
      but nothing ever passes one (`rg -n "custody_chain=" src/` returns
      nothing), so the mission releases the key without modelling the handoffs
      that preceded it. The escrow currently advertises an audit trail the
      mission does not use.
      *Closes when:* either `canonical_mission()` builds a real transfer
      sequence and reports its tip hash as a `RESULT_CUSTODY_*` token, or the
      field is removed and the module docstring corrected.

- [ ] **Resolve `FireControlSolution.closed_loop`.** It is a one-line alias
      returning `self.feasible`, referenced only by tests — it carries no
      information the caller does not already have.
      *Closes when:* it either gains a distinct meaning (e.g. feasible *and*
      inside a maximum engagement range, which would need a range parameter) or
      is removed along with the two assertions that use it.

## Notes

- The six domain modules deliberately carry **no** `bond_api` import;
  `mission.py` is the only adapter, and `canonical_mission()` is the shared
  scenario driver for both the mission outcome and the manuscript tokens.
- `output/` is gitignored and regenerable; regenerating reproduces it
  byte-for-byte, which is the live determinism proof.
- Gates are listed in `AGENTS.md`; the doctrine behind the tests is in
  `docs/testing_philosophy.md`.
