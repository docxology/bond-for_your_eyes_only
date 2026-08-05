# Testing philosophy — for_your_eyes_only (ATAC)

What this package believes a test is for, and what it refuses to accept as one.

## The premise

A passing suite is evidence only to the extent that some realistic mistake
would have made it fail. Coverage measures which lines ran, not which claims
are pinned. So the standard here is not "is it covered" but **"what input would
turn this green assertion red?"** If there is no answer, the test is decoration
and the line it covers is unprotected.

That question is the reason for most of the structure below.

## No mocking framework

`unittest.mock`, `MagicMock`, and `mocker.patch` are prohibited. Every test
uses real inputs and real computation:

- **Field arithmetic** — actual Shamir splits and Lagrange reconstructions over
  the real 61-bit prime, not stand-ins.
- **Filesystem** — real temporary files via pytest's `tmp_path`.
- **CLIs** — real `subprocess` invocations of the actual scripts, parsing the
  actual JSON they print.
- **Figures** — real matplotlib renders through the `Agg` backend to real PNGs.

When a test genuinely needs to drive a failure branch that real inputs cannot
reach, the answer is a **real seam**, not a mock. `generate_variables` accepts a
`metrics_provider` callable defaulting to the live computation; the test passes
an ordinary five-line function that raises. That exercises the actual
strict-versus-draft control flow with real code. Nothing is patched, nothing is
intercepted, and the production default is what production uses.

`monkeypatch` for environment isolation is acceptable; substituting a
dependency is not.

## Determinism

Fixed seed, fixed field, fixed graph, fixed link configuration. Tests assert on
exact values where the mathematics is exact and `pytest.approx` where it is
floating point.

Determinism is itself tested: encoding the same data twice must produce
identical symbols, splitting the same key with the same seed must produce
identical shares, and different seeds must produce different ones. That last
assertion matters — without it, a scheme that ignored its seed entirely would
pass the first two.

**Pinning the variable is not testing it.** The package's determinism claim was
false for a while and the suite could not see it. `SOURCE_DATE` was
`datetime.now()`, so regenerating `output/` wrote different bytes on every run
— but the only determinism test called `generate_variables(now=<fixed>)`,
injecting the one value that varied. The fix has two halves: the stamp is now
resolved from tracked inputs (`SOURCE_DATE_EPOCH`, else the declared
`paper.date`), and `test_scripts_smoke.py` runs the real generator twice into
two roots and diffs every byte of both trees, with a control asserting today's
date appears nowhere in the output. If you must inject a value to make a test
deterministic, ask what the injection is hiding.

## What we insist on

**Positive controls, and the control must touch the mechanism.** A test that
something is rejected is worthless unless something is also accepted, and vice
versa. `verify_share` is tested to accept authentic shares *and* reject
tampered ones.

`test_config_consistency.py`'s control is worth spelling out, because it was
itself hollow. It used to build `dict(declared['escrow'], threshold=THRESHOLD +
1)` and assert `wrong['threshold'] != THRESHOLD` — that is `X + 1 != X`, true of
every integer, touching neither the config loader nor the comparison. The whole
file could have been self-comparing and that control would still have been
green. It now writes a config file with one wrong value, loads it through
`load_manuscript_config`, calls the same `_check_escrow_block` the real test
calls, and requires it to raise — then re-runs it on an unmutated round-trip so
the failure is attributable to the wrong value rather than to serialisation.
A control that does not run the mechanism is decoration with a reassuring name.

**The general case, not the easy case.** The erasure code's entire purpose is
surviving arbitrary fragment loss. Recovering from the *leading* `k` fragments
demonstrates nothing — a decoder that ignored fragment positions would pass it
too. So the suite enumerates all ten three-of-five combinations, and explicitly
includes a set containing none of the leading fragments.

**Derived values, not stapled ones.** `fingerprint_match` is recomputed by
hashing the released key and comparing. It was previously the literal `True`,
which meant `scripts/00_preflight.py`'s escrow verdict could not fail — it
would have reported `[PASS]` no matter what release returned.

The same defect survived one file over: `execute()` returned
`MissionOutcome(success=True, ...)`, so the preflight's `mission_success`
verdict was unfalsifiable by construction. `success` is now
`mission_succeeded(scenario)`, a conjunction of six measured properties of the
computed run, and the test degrades the real frozen `CanonicalMission` one
field at a time (via `dataclasses.replace`) requiring each degradation to flip
the verdict. Verified by hand as well: raising the link's detection threshold
to 800 dB makes `scripts/00_preflight.py` print `[FAIL] mission_success` and
exit 1.

**Guards that fire.** Every validation branch in `src/` is reached by a test
with real inputs: non-invertible modular inverses via a composite modulus, a
singular Vandermonde system via dependent rows, duplicate share points via a
deliberately tiny field, a disconnected routing graph, a negative discriminant
via a faster crossing target. A guard no test reaches is either unreachable —
in which case delete it — or unprotected.

**Meaningful assertions.** `assert x > y * 0` is a disguised `assert x > 0` and
was replaced with a comparison against the actual detection threshold. A test
named `test_unknown_phase_exits_2` that asserted `returncode == 0` was replaced
with one that drives the real unknown-phase path and asserts exit code 2. A
test docstringed "higher risk weight can change the chosen path" asserted
`high.total_cost >= low.distance_nm` and `isinstance(high.path, tuple)` — the
first holds for any non-negative weight on any graph and the second cannot
fail; worse, the behaviour it named is not true of the shipped graph at all.
It was replaced by a two-option graph on which the path demonstrably flips,
plus an explicit pin that the Ionian route is risk-invariant.

**Ordering is weaker than the law.** `cylindrical < spherical` passed while the
spreading term was `20*n*log10(r)` — which made the constant labelled spherical
twice spherical and the one labelled cylindrical exactly spherical. Any
increasing function of the parameter satisfies an ordering test. The
replacement subtracts absorption to isolate the geometry and asserts the
decade slope itself: 20 dB for `SPHERICAL_SPREADING`, 10 dB for
`CYLINDRICAL_SPREADING`.

## Documentation is under test

Two suites exist to stop prose drifting from code:

`tests/test_manuscript_variables.py` fails when a token used in prose has no
generator, and again when a rendered section still contains an unsubstituted
placeholder. This is what makes "every number is injected" enforceable rather
than aspirational — during this pass it caught a literal token in a sentence
*about* tokens.

`tests/test_config_consistency.py` pins each value declared in
`manuscript/config.yaml`'s `mission:` block to the constant the mission
actually executes with. The block had previously drifted into declaring an
escrow key of 4242 that no code path read; the pin makes that class of decay a
test failure.

## The gate

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
```

Branch coverage is enabled, so a partially-taken conditional counts as a gap.

Test counts and coverage percentages are deliberately **not** quoted in this
file or in the manuscript. A number typed into prose is a snapshot that decays
on the next commit and then quietly misinforms. The gate is the durable claim;
the measurement is whatever the command prints today.

## Structure

| File | Binds |
|---|---|
| `test_key_escrow.py` | Shamir round-trips, commitments, quorum and tamper rejection, custody chaining |
| `test_key_recovery.py` | Encode/recover round-trips, exhaustive any-`k` recovery, checksum corruption detection |
| `test_underwater_retrieval.py` | Tissue saturation, no-decompression limits, descent/ascent scheduling, drift |
| `test_island_routing.py` | Route optimality, Dijkstra/A* agreement, risk-driven path selection on a two-option graph, and the Ionian graph's risk-invariance |
| `test_targeting.py` | Intercept feasibility, lead-angle geometry, closest-approach fallback |
| `test_acoustic_link.py` | Thorp absorption, path loss, SNR monotonicity, margin semantics, bisection |
| `test_mission.py` | Frozen protocol conformance, gadget registry, provenance, canonical scenario |
| `test_figures.py` | Real PNG rendering, deterministic output |
| `test_manuscript_variables.py` | Token generation, strict resolution, deterministic build stamp |
| `test_manuscript_crossrefs.py` | Bib keys ↔ citations, figure labels ↔ references ↔ generators |
| `test_config_consistency.py` | Declared config pinned to executed constants |
| `test_error_paths.py` | Every validation guard, driven by real inputs |
| `test_scripts_smoke.py` | Real subprocess runs of each phase CLI; byte-identical regeneration |
