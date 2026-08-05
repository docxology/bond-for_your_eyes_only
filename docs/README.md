# `docs/` — for_your_eyes_only (ATAC)

Developer and agent documentation for the PROJECT BOND film package
**For Your Eyes Only (1981)**, mission codename **ATAC**.

This directory explains *how the package is built and why it is built that
way*. It is distinct from the two neighbouring bodies of writing:

| Where | Audience | Contains |
|---|---|---|
| `../README.md` | someone meeting the package | what it is, module list, how to run it |
| `../manuscript/` | a reader of the scientific report | the ATAC mission mathematics and its computed results |
| **`docs/` (here)** | a developer or agent changing the code | architecture, working rules, testing doctrine |

## Contents

| File | What it answers |
|---|---|
| [`architecture.md`](architecture.md) | What each `src/` module computes, how the layers compose, and how `mission.py` satisfies the frozen `bond_api` MissionProvider |
| [`agent_instructions.md`](agent_instructions.md) | Concrete operational instructions: commands, task recipes, what to verify before claiming done |
| [`AGENTS.md`](AGENTS.md) | The rules an agent works under inside this package — scope, invariants, and the traps specific to ATAC |
| [`testing_philosophy.md`](testing_philosophy.md) | The no-mock / real-data / determinism doctrine and what counts as a test that actually binds something |

## Orientation in one paragraph

ATAC is a lost-key recovery mission. A targeting-communicator's cryptographic
key is escrowed across custodians so no single holder can release it, and
erasure-coded so no single lost fragment destroys it. The device itself sits on
a wreck, so reaching it requires a dive plan that survives depth and current;
getting to the dive site requires a route across the Ionian islands; and once
recovered, the device must produce a firing solution against a moving contact
and uplink it acoustically. Six pure mathematical modules implement those six
ideas, and one thin adapter exposes them to the BOND suite as a mission.

## The load-bearing invariant

Everything in this package is deterministic, and one function —
`mission.canonical_mission()` — is the single source of truth for the mission's
outputs. Both the protocol's `execute()` results and the manuscript's injected
numbers read from it. That is why the report cannot disagree with the code: it
is not that the two are kept in sync, it is that there is only one of them.

If you change what the mission computes, you change `canonical_mission()`, and
both the mission outcome and every manuscript number follow. If you find
yourself typing a number into prose, you have stepped outside this invariant —
see [`agent_instructions.md`](agent_instructions.md#adding-a-result-to-the-manuscript).

## Lineage

The package was forked from the template repository's
`template_code_project` exemplar and then rewritten for ATAC. That lineage
explains the layout conventions (pure `src/`, thin `scripts/`, tokenised
manuscript, per-project coverage gate) but no exemplar content remains — the
domain modules, tests, and manuscript are all ATAC-specific.
