# tests/ — agent guidance

The reader's view is [README.md](README.md); the package rules are in [the root guide](../AGENTS.md),
[`docs/AGENTS.md`](../docs/AGENTS.md) and [`docs/agent_instructions.md`](../docs/agent_instructions.md);
the doctrine is [`docs/testing_philosophy.md`](../docs/testing_philosophy.md).

## Run it

From the repository root:

```bash
python -m pytest tests/ -q --cov=src --cov-fail-under=90
```

The documented form in the root guide is `uv run pytest tests/ ...`. Prefer the interpreter form
(`python -m pytest`): a relocated `.venv` can leave a `pytest` console script that runs a different
environment's pytest and exits zero, which reads as a gate that passed when it never ran. The suite
prints the test count and the coverage it measured; the root guide's checklist asks you to report those
in your work note together with the commit SHA, rather than writing them into prose that drifts.

A worktree cut outside the vault has no `.venv` and no sibling `../bond-api` checkout, which
`[tool.uv.sources]` in `pyproject.toml` needs. Run it with an interpreter that already exists — for
example the parent repository's `.venv/bin/python`. No other setting is required: `pyproject.toml` sets
`pythonpath = [".", "src"]`, and `conftest.py` also inserts `src/` and the repository root.

**Dated:** as of 2026-11-03 the vendoring change in this suite replaces the `../bond-api` path
dependency with a `vendor/bond-api` directory, after which an ordinary `uv sync` in a worktree resolves
locally. Re-check this paragraph if that change has landed here.

## Rules

- **Zero mocks.** No `MagicMock`, `unittest.mock` or `mocker.patch` anywhere in this directory; the
  repository's own check is `rg -n "MagicMock|unittest\.mock|mocker\.patch" tests/` (run at `0f81318`
  on 2026-11-03, no match). Where a failure path needs driving, use a real injectable seam.
- **The coverage floor is a gate, not a target**: `--cov-fail-under=90` on `src/`, line and branch,
  with zero failures and zero skips expected.
- **Determinism**: one fixed seed, `mission.MISSION_SEED` in `src/for_your_eyes_only/mission.py`, no
  untracked RNG, and no wall-clock value in any persisted artifact.
- **A boolean verdict must be derivable.** `fingerprint_match` is recomputed and compared rather than
  stapled to `True`, because `scripts/00_preflight.py` reads it as a pass/fail verdict. Before adding
  a boolean of that kind, ask which input would make it `False`; if there is no answer, it is not a
  check.
- **Keep the erasure test exhaustive.** The decoder's generality is the feature; the combination
  enumeration is what makes the any-`k` claim real.
- **New public functions go in `__all__`**, which is hand-maintained in `src/`.
- **A constant change moves its mirrors.** `manuscript/config.yaml`'s `mission:` block is pinned to the
  `mission.py` constants by `test_config_consistency.py` — change one and change the other.

## What is absent here

No CI: this repository carries no `.github/` directory, so nothing runs the suite unless a person or a
lane invokes it. There is also no recorded baseline file — the suite prints what it measured, and the
root guide's checklist says where that goes.
