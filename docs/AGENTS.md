# Working inside for_your_eyes_only (ATAC) — rules for agents

Read [`architecture.md`](architecture.md) first for what the modules do. This
file is the set of rules you work under. For step-by-step commands and task
recipes see [`agent_instructions.md`](agent_instructions.md).

## Scope

Your scope is **exactly this directory**. Do not edit a sibling BOND package,
the files at the bond root, or the template repository. If your change appears
to require touching a sibling, it does not belong here — record it as an
integration point in `../TODO.md` instead.

The only permitted remote is `origin`
(`github.com/docxology/bond-for_your_eyes_only`). Commit here; push only there,
and never to a sibling BOND package or the template repository.

## Hard invariants

These are not style preferences. A change that breaks one of them is wrong even
if the tests pass.

**1. The frozen protocol surface does not change.**
`mission.MissionProvider` (`brief` / `recon` / `plan` / `execute` / `debrief`)
and the module-level `GADGETS` registry are consumed by `bond-cli`, the
coordinator, and the orchestrator across package boundaries. Deepen *inside*
the package — new domain modules, richer mission internals, more results in the
outcome dict — but never rename, re-signature, or remove those.

**2. `src/` holds the mathematics; `scripts/` holds none of it.**
Scripts parse arguments, wire imports, and print. The moment a script computes
something a reader would cite, that computation belongs in a domain module with
a test.

**3. The six domain modules stay infrastructure-free.**
`key_escrow`, `key_recovery`, `underwater_retrieval`, `island_routing`,
`targeting`, and `acoustic_link` must remain importable without `bond_api`
installed. `mission.py` is the only adapter. Do not add a suite import to a
domain module for convenience.

**4. No mocking framework.**
No `unittest.mock`, no `MagicMock`, no `mocker.patch`. Real data, real
computation. When a test needs to drive a failure path, add a genuine seam — an
injectable callable parameter with a real default — and pass an ordinary
function. `generate_variables(metrics_provider=...)` is the worked example.

**5. Determinism.**
One fixed seed (`mission.MISSION_SEED`). No wall-clock value in any persisted
artifact — `Provenance.wall_time_s` is deliberately `0.0`, and the build stamp
(`SOURCE_DATE`) is derived from tracked inputs (`SOURCE_DATE_EPOCH`, else the
manuscript's declared `paper.date`), injectable in tests via
`generate_variables(now=...)`. Regenerating `output/` must reproduce it
byte-for-byte.

**6. Every manuscript number is injected.**
Never type a metric into prose. Add it to `manuscript_variables` and reference
the token. See
[`agent_instructions.md`](agent_instructions.md#adding-a-result-to-the-manuscript).

**7. Coverage, lint, and types gate the work.**
`--cov-fail-under=90` on `src/`, ruff check and format clean, mypy clean on
`src/` and `scripts/`.

## Traps specific to this package

**`canonical_mission()` is the single source of truth.** If you compute a
mission quantity anywhere else — in a script, in a figure, in the manuscript
hydrator — you have created a second source that can disagree with the first.
Add a field to `CanonicalMission` instead.

**Verdicts must be derivable.** `fingerprint_match` is recomputed and compared,
not set to `True`, because `scripts/00_preflight.py` reads it as a pass/fail
verdict. Any new boolean the preflight or the manuscript consumes must be
derived the same way. Before adding one, ask: *what input would make this
False?* If there is no answer, it is not a check.

**`manuscript/config.yaml`'s `mission:` block is a mirror, not an input.** No
manuscript number comes from it; every number is computed from the constants in
`mission.py`. The block is pinned to those constants by
`tests/test_config_consistency.py`. If you change a mission constant, change
the config block too — the test will tell you. Do not add a value to the block
that the code does not actually use; that is how it previously came to declare
an escrow key of 4242 that nothing read.

**The erasure decoder's generality is the feature.** `recover_erasure` accepts
an explicit `indices` set. A test that only recovers from the leading `k`
fragments proves nothing about erasure coding — it is exactly what a decoder
that ignored fragment positions would also pass. Keep the exhaustive
combination test.

**`__all__` is maintained by hand.** When you add a public function to a domain
module, add it to `__all__`. Several modules previously omitted their primary
entry points.

## What to report when you finish

State the coverage percentage and test count you actually observed in the
command output, the commit SHA, and anything you could not verify. Do not
report a number you did not read from a command you ran. If a gate did not run,
say so — an unrun gate is not a passing gate.
