# TODO — for_your_eyes_only (ATAC)

PROJECT BOND film package for **For Your Eyes Only (1981)**, mission codename
**ATAC**: threshold key escrow, erasure-coded key survival, Haldane dive
planning, Ionian insertion routing, fire-control intercept, and an underwater
acoustic link budget, all behind a frozen `bond_api.MissionProvider`. Scope is
exactly this directory; local-only tree, no remote.

**Verified state today** (measured this session at `949bd24`, working tree
clean): `uv run pytest tests/ --cov=src --cov-fail-under=90` → **175 passed,
0 failed, 0 skipped, 100.00% line+branch coverage** across all nine modules in
`src/for_your_eyes_only/` (Python 3.14.6, pytest 9.0.2). Every one of the 11
findings in `output/verify/for_your_eyes_only.json` was re-checked against the
current tree and is resolved; the package produced no
`for_your_eyes_only.unresolved.json` and does not appear in the suite-wide
`output/verify/_unresolved.json`. **Nothing below is carried over from an
unresolved audit finding** — the open items are ones this pass found by reading
the code, plus the integration points that were never bound.

Completed work is not tracked here; `git log` is the record.

---

## Open work

### Correctness

**C1 — `FireControlSolution.closed_loop` promises more than it returns.**
`src/for_your_eyes_only/targeting.py:62-65` defines a property named
`closed_loop` whose entire body is `return self.feasible`. "Closed loop" names
a guidance regime (the weapon corrects against continuous target updates); the
value it returns is only "the intercept quadratic has a positive root". It is
referenced from nowhere in `src/` or `scripts/` — only
`tests/test_targeting.py:59` and `:86` read it, so the two assertions that
"cover" it are asserting `feasible` twice under a second name.
*Done when:* the property either carries information `feasible` does not (e.g.
feasible **and** intercept range within a maximum engagement range, which needs
a new range parameter on the solution), or is deleted along with the two
assertions and any mention in `docs/architecture.md`.
*Demonstrate:* `rg -n "closed_loop" src/ tests/ scripts/ docs/` — every
surviving hit must be a use that `feasible` could not satisfy; then
`uv run pytest tests/test_targeting.py -v` and the coverage gate stay green.

**C2 — `EscrowState.custody_chain` is a permanently empty field behind a
documented audit trail.** `src/for_your_eyes_only/key_escrow.py:105` declares
`custody_chain: tuple[CustodyTransfer, ...] = field(default_factory=tuple)`,
and `generate_custody_transfer` (`key_escrow.py:264`) plus `custody_chain_hash`
(`key_escrow.py:258`) implement a real SHA-256 hash chain. Nothing ever passes
one: `rg -n "custody_chain=" src/ tests/ scripts/` returns **zero** hits, so
every `EscrowState` in this package ships with an empty chain.
`docs/architecture.md:45-46` describes the pair as "a SHA-256 hash-chained
ledger of handoffs, making custody auditable and append-only" — true of the
functions, but the mission releases the ATAC key without modelling a single
handoff, so the package advertises an audit trail it never produces.
*Done when:* either `canonical_mission()`
(`src/for_your_eyes_only/mission.py`) builds a real transfer sequence, stores
it on the escrow, and reports its tip hash as a `RESULT_CUSTODY_*` manuscript
token; **or** the field, the two functions, and the `docs/architecture.md`
bullet are removed together.
*Demonstrate:* `rg -n "custody_chain" src/ docs/ manuscript/` shows no orphan,
and — for the first option — `uv run python scripts/execute.py | rg custody`
prints a non-empty tip hash that
`uv run pytest tests/test_manuscript_variables.py -v` pins as a token.

### Verification

**V1 — the `finite_dive_time` preflight verdict cannot fail.**
`scripts/00_preflight.py:44` appends `("finite_dive_time", plan.total_time_s >
0)`. `RetrievalPlanner.plan()`
(`src/for_your_eyes_only/underwater_retrieval.py:321`) always descends and
always ascends, so `total_time_s` is positive for every constructible planner;
no input turns this verdict red. It is the last survivor of the pattern that
`mission_succeeded()` (`src/for_your_eyes_only/mission.py:257-274`) and its
degradation control (`tests/test_mission.py:96-117`) eliminated everywhere
else, and `AGENTS.md`'s "Verdicts must be derivable" trap claims the pattern is
gone.
*Done when:* the verdict is replaced by one a degraded input can fail — e.g.
`plan.total_time_s <= no_decompression_limit(model, wreck_depth)`, or bottom
time within the planner's own budget — **and** a test constructs a planner
configuration that makes `00_preflight.py` exit non-zero on exactly that line.
*Demonstrate:* `uv run pytest tests/test_scripts_smoke.py -v` contains a case
asserting a non-zero exit with `[FAIL] finite_dive_time` in stdout, alongside
the existing `test_preflight_all_pass`.

### Documentation

**D1 — the ambient-noise model is the one channel term with no source.**
`src/for_your_eyes_only/acoustic_link.py:88-102` returns
`55.0 + 12.0 * math.log10(1.0 + sea_state)` under the docstring claim "typical
values run ~55-75 dB for mild seas at mid frequencies". That functional form is
not from the literature. Every other term in the same module is cited —
absorption to Thorp (`references.bib` `thorp1967analytic`), the sonar equation
to Urick (`urick1983principles`) — and `manuscript/02_methodology.md:136-137`
says only that NL "is computed from a declared sea state", which is honest but
leaves the module docstring making an uncited physical claim. The canonical
reference for sea-state ambient noise (Wenz 1962) is absent from
`manuscript/references.bib`.
*Done when:* either the docstring states plainly that the form is an
illustrative monotone stand-in rather than a published curve; **or** a real
source is cited, added to `references.bib`, and cited from prose — note that
`tests/test_manuscript_crossrefs.py:55` requires every bib key to be cited in a
numbered section, so adding the entry without citing it will fail the gate.
*Demonstrate:* `uv run pytest tests/test_manuscript_crossrefs.py -v` green, and
`rg -n "55-75 dB" src/` returns nothing unless a citation sits beside it.

### Extension

**E1 — wire the decompression ceiling into ascent staging.**
`HaldaneModel.ceiling_m` (`src/for_your_eyes_only/underwater_retrieval.py:130`)
and `no_decompression_limit` (`:150`) are implemented and tested, but
`plan_descent` (`:191`, staging loop at `:232`) climbs in fixed `STOP_INTERVAL`
steps at a fixed `ASCENT_RATE` without reading any tissue state — the module
docstring (`:30`) and `plan_descent`'s own docstring (`:205-208`) say so. This
is a stated limitation (see below), so it is scheduled work, not a live defect.
*Done when:* stop depths and durations are derived from compartment ceilings.
*Demonstrate:* a test showing a deeper wreck **or** a longer bottom time
produces more stops or longer stop durations — a pair of planner
configurations whose stop **schedules** differ, not merely whose totals differ:
`uv run pytest tests/test_underwater_retrieval.py -v`.

**E2 — persist provenance through `bond-utilities` (now unblocked).**
`MissionProvider.execute()` (`src/for_your_eyes_only/mission.py:359`,
`Provenance(...)` at `:434-439`) returns package version, seed, input hash and
`wall_time_s=0.0` **in memory only** — nothing is written. The dependency has
since shipped: `bond-utilities/src/bond_utilities/mission_io.py:153` now
exposes `record_provenance_outcome(mission_id, seed, version, input_payload,
outcome, path, fmt=..., codename=..., started_at=..., now=...)`, and it takes a
`now` clock override, so binding it need not reintroduce wall-clock into a
persisted artifact. Note `started_at` defaults to `datetime.now(timezone.utc)`
— pass `now` or `started_at` explicitly or the determinism gate
(`tests/test_scripts_smoke.py:90`, `:111`) will catch it.
*Done when:* `execute()` (or a thin script over it) writes a record and a test
reads it back off disk.
*Demonstrate:* a test asserting the persisted record's
`provenance.input_hash` equals the in-memory `Provenance.input_hash` for the
same run, plus `uv run pytest tests/test_scripts_smoke.py -v` still byte-clean.

**E3 — confirm ATAC through the coordinator's reconcile step.** Discovery is
verified here only against a direct
`bond_api.load_provider("for_your_eyes_only")`
(`bond-api/src/bond_api/discovery.py:82`). The coordinator carries the slug as
a hand-written ROSTER row
(`bond-coordinator/src/bond_coordinator/registry.py:208`), and the live merge
path is `reconcile.override_codenames` (`reconcile.py:78`) and
`reconcile.harvest_gadgets` (`reconcile.py:109`), which consume each film's
`MissionBrief.codename` (`mission.py:287`, `ATAC_MISSION`) and module-level
`GADGETS`. Neither has been exercised against this package. Nothing in *this*
directory blocks it; the check belongs to whoever runs the fleet.
*Done when:* a reconcile run reports ATAC's own codename and gadget names as
harvested from this package, overriding the coordinator's provisional row.
*Demonstrate:* from the bond root, a reconcile report listing
`for_your_eyes_only` with codename `ATAC` and this package's `GADGETS` keys —
run the coordinator's gate, not a hand-written assertion in this package.

---

## Known limitations (not bugs)

- **`risk_weight` never changes the chosen route on the shipped Ionian
  graph.** The audit found the old risk-sensitivity test asserted
  `high.total_cost >= low.distance_nm` and an `isinstance` check — neither
  could fail. The claim was corrected rather than the graph: the
  least-distance and least-risk corridors coincide for every node pair on the
  real geography, so `risk_weight` always changes a route's **cost** and never
  its **choice**. That invariance is now pinned by
  `tests/test_island_routing.py::test_ionian_graph_route_is_risk_invariant`,
  and the mechanism is exercised on an explicit two-option graph in
  `test_risk_weight_changes_the_chosen_path`. The scope note lives in the
  `island_routing.py` module docstring and in `README.md`'s module table. Do
  not "fix" this by perturbing edge weights until the choice flips — that would
  be authoring geography to satisfy a test.

- **Ascent staging is geometric, not tissue-driven.** See E1. Until E1 lands,
  the honest scope is: the Haldane compartments, `ceiling_m`, and
  `no_decompression_limit` are real and tested, but the ascent schedule does
  not consult them. `manuscript/02_methodology.md`, the module docstring
  (`underwater_retrieval.py:30`), and `plan_descent`'s docstring (`:205-208`)
  all state this rather than implying a decompression-driven profile.

- **`Provenance.wall_time_s` is the literal `0.0`.** It is not a measurement
  and is not meant to be one: any real timing value would make `output/`
  non-reproducible and break
  `tests/test_scripts_smoke.py::test_regenerating_the_artifact_tree_is_byte_identical`.
  Determinism is the priority; the field exists to satisfy the frozen
  `bond_api` shape.

- **The six domain modules deliberately import no `bond_api`.** `mission.py` is
  the only adapter, and `canonical_mission()` is the single scenario driver
  behind both the mission outcome and the manuscript tokens. This is an
  architectural rule, not an omission — the domain modules must stay importable
  standalone.

- **`manuscript/config.yaml`'s `mission:` block is a mirror, not an input.** It
  is pinned to the `mission.py` constants by `tests/test_config_consistency.py`;
  changing a constant requires changing the block. Adding a value nothing reads
  is a defect, not a feature.

- **No test count or coverage figure is quoted in `README.md`.** Deliberate:
  the gate command is the durable claim and prints today's measurement. The
  figures at the top of this file carry a commit SHA precisely because they go
  stale.

---

## Verification

Run from this directory. All must be green before any commit.

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
# expected: 175 passed, 0 skipped; "Total coverage: 100.00%" (floor 90%, branch on)

uv run ruff check src/ scripts/ tests/          # expected: "All checks passed!"
uv run ruff format --check src/ scripts/ tests/ # expected: no files would be reformatted
uv run mypy src/ scripts/                       # expected: no issues

uv run python scripts/00_preflight.py           # expected: 7 [PASS] lines, exit 0
uv run python scripts/z_generate_manuscript_variables.py  # regenerates output/, exit 0

rg -n "MagicMock|unittest\.mock|mocker\.patch" tests/   # expected: no matches (no-mock policy)
rg -n "template[_]code_project" . --glob '!uv.lock' --glob '!.git/**'
                                                 # expected: lineage prose only
git status                                       # expected: clean after committing
```

If `uv` reports `Failed to initialize cache at ~/.cache/uv`, that is a sandbox
restriction, not a package failure — re-run the same command unsandboxed.

A gate you did not run is not a gate that passed. Report the coverage
percentage and test count you actually observed, plus the commit SHA.
