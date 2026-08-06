# Architecture — for_your_eyes_only (ATAC)

How this package is put together, module by module, and how it plugs into the
BOND suite.

## Layer topology

```
scripts/                     thin CLIs — argument handling and JSON printing only
  brief.py recon.py plan.py execute.py debrief.py
  00_preflight.py  z_generate_manuscript_variables.py
        |  (import, never reimplement)
        v
src/for_your_eyes_only/mission.py        the ONLY module importing bond_api
        |  frozen MissionProvider + GADGETS + canonical_mission()
        v
src/for_your_eyes_only/  six pure domain modules — no bond_api, no infrastructure
  key_escrow  key_recovery  underwater_retrieval
  island_routing  targeting  acoustic_link
        |
        +--> figures.py             deterministic matplotlib rendering
        +--> manuscript_variables.py token hydration for the manuscript
```

The direction of dependency is strictly downward. The six domain modules import
nothing from the suite and nothing from each other except `key_recovery`, which
reuses `key_escrow`'s prime field and modular inverse rather than defining a
second one. That single edge is deliberate: the erasure code and the secret
share scheme must live in the *same* field for the recovered fragments to be
meaningful.

## The six domain modules

### `key_escrow.py` — custody and quorum release

Implements **Shamir secret sharing** over `GF(p)` with the 61-bit Mersenne
prime `p = 2^61 - 1`. The ATAC key is the constant term of a random degree
`k-1` polynomial; each custodian receives one point. Any `k` points recover the
key by Lagrange interpolation at `x = 0`; fewer than `k` reveal nothing.

Also provides:

- `commit_share` / `verify_share` — a share is committed as `g^y mod p`, so a
  share tampered with during custody is rejected before it can be used.
- `custody_chain_hash` / `generate_custody_transfer` / `custody_chain_for` /
  `custody_chain_is_consistent` — a SHA-256 hash-chained ledger of handoffs,
  making custody auditable and append-only. The mission binds a real chain
  (built over its custodians) to the escrow at creation and reports its tip,
  rather than leaving the field empty.
- `create_escrow` / `release_key` — the high-level API. `release_key` verifies
  each share against its commitment, reconstructs, then confirms the result
  reproduces the escrow's stored key fingerprint.
- `KEY_BOUND` — the exclusive upper bound (`2^32`) for a seed-derived key, kept
  well inside the field.

### `key_recovery.py` — erasure-coded survival

A **systematic Reed–Solomon-style erasure code over `GF(p)`**. The key becomes
`k` data symbols; a generator polynomial is evaluated at `n` distinct field
points to yield `n` stored fragments, plus an optional integrity checksum
symbol.

`recover_erasure` takes an explicit `indices` tuple naming which fragments
survived and solves that Vandermonde subsystem. This is the module's whole
point: a decoder hard-wired to the leading `k` fragments would pass a
round-trip test while being unable to survive the loss of fragment 0. Because
any square Vandermonde matrix over a field is invertible, *any* `k` of the `n`
fragments reconstruct the key, and the test suite enumerates every combination
to prove it.

Requesting checksum verification when no checksum symbol is present raises
rather than silently skipping — a caller asking to be protected must never be
told that nothing was wrong.

### `underwater_retrieval.py` — reaching the wreck

Three pieces of real physics:

- **Haldane tissue model** (`HaldaneModel`, `tissue_saturation`) — independent
  compartments whose pressure relaxes exponentially toward ambient with time
  constant `tau = t_half / ln 2`. M-values are validated to exceed 1.0, since
  an M-value is a multiple of surface pressure and a value at or below 1.0
  would describe a tissue that cannot survive the surface.
- **No-decompression limit** (`no_decompression_limit`) — the exposure at which
  the limiting compartment first saturates to its ceiling,
  `t_i = tau_i * ln((P_amb - 1)/(P_amb - M_i))`. Returns `inf` at the surface
  and at depths shallow enough that no compartment can ever reach its ceiling.
- **Current-drift compensation** (`current_offset`) — over a total dive time
  `T` under constant current `(u, v)`, the bell must start offset by `T*(u,v)`
  upstream to land on the wreck.

`plan_descent` assembles a descent/bottom/staged-ascent profile; the ascent
stops are snapped to a fixed interval and each stop's duration is sized by
`decompression_ascent_stages` against the compartment ceilings of a Haldane
model, so a deeper wreck or a longer bottom exposure produces larger or more
stops. The parameters are classroom-grade (proportional M-value ceilings, not a
field-validated Bühlmann line), stated plainly in the module docstring and in
`07_scope_and_related_work.md`. `RetrievalPlanner` binds depth, current, and
bottom time into a `RetrievalPlan` and reports whether the required drift
offset is inside the operational envelope.

### `island_routing.py` — the insertion route

A weighted undirected graph of Ionian harbours with fixed positions on a
nautical-mile grid. Edges carry a distance and a risk weight; cost is
`distance + risk_weight * risk`, so a planner *can* be told to prefer a safe
passage over a short one — but on this graph it never has to: the safest and
shortest corridors coincide for all 28 node pairs, so `risk_weight` changes
route cost and never route choice. Both halves are pinned in
`tests/test_island_routing.py`, the selection mechanism on a separate
two-option graph.

`plan_route` runs **Dijkstra**, or **A\*** with the straight-line admissible
heuristic when `use_astar=True` — the same optimum, reached with less
expansion. `edge_distance` raises on a non-adjacent pair rather than falling
back to a straight-line guess: consecutive nodes of a planned route are
adjacent by construction, so a miss means the caller made a mistake that should
surface rather than be papered over with a smaller number.

### `targeting.py` — the firing solution

The classical **constant bearing, decreasing range** intercept. A weapon at the
origin with speed `v_w` meets a target at `p0` moving with velocity `v_t` when
`|p0 + v_t t| = v_w t`, which squares to

```
(|v_t|^2 - v_w^2) t^2 + 2(p0 . v_t) t + |p0|^2 = 0
```

Three branches, all reachable and all tested:

- the quadratic term vanishes (equal speeds) → linear equation;
- negative discriminant (a faster target crossing abeam) → no real root;
- a positive root → intercept time, weapon course `u = (p0 + v_t t)/(v_w t)`,
  and the lead angle as the angle between `u` and the line of sight.

`closest_approach` is always computed, so an infeasible engagement still
reports the useful quantity: how near the weapon gets.

### `acoustic_link.py` — the uplink budget

The sonar equation. **Thorp's formula** gives frequency-dependent absorption in
dB/km; `transmission_loss` adds geometric spreading as `10 * n * log10(r)` for
a spreading *exponent* `n` (`SPHERICAL_SPREADING = 2.0` → 20 dB per decade,
`CYLINDRICAL_SPREADING = 1.0` → 10 dB per decade). The mission's wreck uplink
is a shallow-water horizontal channel and uses the cylindrical exponent.
Received SNR is `SL - TL - NL + DI`, and the link *closes* when SNR reaches the
detection threshold `DT`. `NL` is not a hand-typed literal: it is
`noise_level(ATAC_SEA_STATE)`, so the declared sea state is what sets it.

`LinkBudget` carries `detection_threshold_db` alongside the SNR so `margin_db`
is a real margin (`SNR - DT`, negative when the link is short) rather than a
restatement of the SNR, and `closes` is exactly `margin_db >= 0`.

`max_link_range` bisects for the root of `SNR(r) = DT`. Bracket endpoints are
reported honestly: a link failing at the bracket floor has a coverage radius of
**zero**, not a radius equal to the floor.

## The adapter: `mission.py`

The only module that imports `bond_api`. It provides three things the suite
consumes, whose public shape is frozen:

**1. `MissionProvider`** — the five-stage protocol.

| Stage | Returns | What ATAC does |
|---|---|---|
| `brief()` | `MissionBrief` | Declares the recovery objectives, the escrow asset (threshold, share count, fingerprint), and the determinism/quorum constraints |
| `recon(ReconRequest)` | `ReconReport` | Findings on the goal, the escrow's quorum geometry, the constraints, and route availability |
| `plan(MissionBrief)` | `MissionPlan` | Six ordered `Step`s: `escrow_release`, `key_recovery`, `underwater_retrieval`, `island_routing`, `targeting`, `acoustic_link` |
| `execute(MissionPlan)` | `MissionOutcome` | Runs each step against the domain modules, returns a result block per step plus `Provenance` (version, seed, input hash, zero wall time) |
| `debrief(MissionOutcome)` | `Debrief` | The outcome plus standing lessons |

**2. `GADGETS`** — a module-level `dict[str, object]` built by `build_gadgets()`,
mapping gadget names to the domain callables and prepared state the orchestrator
may invoke.

**3. Mission constants** — `MISSION_SEED`, `ESCROW_THRESHOLD`, `ESCROW_SHARES`,
`CUSTODIANS`, `RECOVERY_DATA_SYMBOLS`, `RECOVERY_CODE_SYMBOLS`, `ROUTE_ORIGIN`,
`ROUTE_DESTINATION`, `ROUTE_RISK_WEIGHT`, `ATAC_LINK`, `ATAC_LINK_RANGE_M`.
These are public because `manuscript/config.yaml` mirrors them and
`tests/test_config_consistency.py` pins the two together.

`bond-cli`, the coordinator's reconcile step, and the orchestrator all consume
the provider and `GADGETS` across packages. **Deepen inside the package; do not
change these shapes.**

## `canonical_mission()` — one scenario, two consumers

```
                   canonical_mission()
                    /              \
    MissionProvider.execute()    manuscript_variables._compute_mission_metrics()
            |                              |
     outcome.results               {{TOKEN}} values in manuscript/
```

`CanonicalMission` is a frozen dataclass holding the typed domain objects for
one deterministic run: the released key and its `fingerprint_match`, the
erasure code and its data/encoded/recovered symbols, the `RetrievalPlan`, the
`RoutePlan`, the `FireControlSolution`, the `LinkBudget`, and the wreck depth.

Because both consumers read the same object, the mission outcome and the
manuscript cannot disagree. `fingerprint_match` in particular is computed by
recomputing SHA-256 over the released key and comparing — never stapled to
`True` — because `scripts/00_preflight.py` turns that same value into a
pass/fail verdict, and a stapled literal would make the verdict unfalsifiable.

## Supporting modules

**`figures.py`** renders four deterministic PNGs via the `Agg` backend:
`island_graph`, `dive_profile`, `targeting_geometry`, `acoustic_link`. It
imports `ATAC_LINK` and `ATAC_LINK_RANGE_M` from `mission` so the figures show
the same configuration the mission runs.

**`manuscript_variables.py`** hydrates every `{TOKEN}` used in
`manuscript/NN_*.md`. `METRIC_TOKENS` is *derived* from a canonical run rather
than hand-listed, so the draft-mode `N/A` fallback cannot drift out of step
with the live metric set. `generate_variables` takes an injectable
`metrics_provider` — a real seam that lets tests drive the strict-versus-draft
branch with an ordinary failing function, no mocking framework involved.
`resolve_manuscript_tree` copies each numbered section to `output/manuscript/`
with tokens substituted, and fails in strict mode if any placeholder survives.

## Scripts are thin

Every file in `scripts/` handles argument parsing, import wiring, and output
formatting only. `_common.py` holds `run_phase`, which dispatches on the
script's own filename to the matching protocol stage and raises `ValueError` for
anything outside the five. No script computes a mission quantity; if a script
starts doing arithmetic that matters, that arithmetic belongs in `src/`.
