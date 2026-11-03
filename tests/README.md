# tests/ — the suite that holds the mission together

One test module per domain capability, plus the adapter, the manuscript gates, the figures and the
CLIs. Everything here runs on real computation and real data; the doctrine and its reason are in
[`docs/testing_philosophy.md`](../docs/testing_philosophy.md).

| Module | Subject |
| --- | --- |
| `test_key_escrow.py` | Shamir escrow, commitments, the custody chain, quorum release |
| `test_key_recovery.py` | Erasure-coded any-`k`-of-`n` recovery, over the exhaustive surviving-fragment combinations |
| `test_underwater_retrieval.py` | Haldane dive and decompression planning against depth and current |
| `test_island_routing.py` | Ionian insertion routing |
| `test_targeting.py` | The fire-control intercept solution |
| `test_acoustic_link.py` | The underwater acoustic link budget |
| `test_error_paths.py` | Every guard across the domain modules, driven through a real seam rather than a mock |
| `test_mission.py` | Protocol conformance, the gadget registry, the full flow |
| `test_config_consistency.py` | `manuscript/config.yaml`'s `mission:` block pinned to the `mission.py` constants it mirrors |
| `test_manuscript_variables.py` | Token hydration and the token cross-reference gate |
| `test_manuscript_crossrefs.py` | Citations and figure references bound to the things they name |
| `test_figures.py` | The deterministic figure generators |
| `test_scripts_smoke.py` | The mission-phase CLIs, in subprocesses |

## What the suite is for

It is where the repository's claims become checkable: known-value assertions on the six domain models,
the adapter conforming to the frozen protocol, the manuscript's tokens and cross-references resolving,
and the CLIs running for real. Two habits here are deliberate rather than incidental. The error-path
tests drive each guard through a real injectable seam instead of mocking it, so a guard that stops
working fails a test rather than being bypassed. The erasure-decoder test enumerates every
surviving-fragment set, which is what makes the any-`k` recovery claim real rather than sampled.

## Where to go next

[`docs/testing_philosophy.md`](../docs/testing_philosophy.md) for the doctrine; `conftest.py` for the
two things every invocation depends on (an `Agg` matplotlib backend for headless figure rendering, and
`src/` plus the repository root on `sys.path`); the root guide's verification checklist for the gate
and the lint and type commands that run alongside it.
