# scripts — ATAC mission phase CLIs

Thin orchestrators only; all business logic lives in `src/for_your_eyes_only/`.

| Script | Purpose |
|---|---|
| `brief.py` | Print the mission brief (deterministic JSON) |
| `recon.py` | Print recon findings (accepts an optional goal) |
| `plan.py` | Print the plan steps |
| `execute.py` | Run the plan and print the outcome |
| `debrief.py` | Summarise outcome + lessons |
| `00_preflight.py` | End-to-end verdicts; exits 0 iff all pass |
| `z_generate_manuscript_variables.py` | Write tokens + resolve manuscript + render figures |

Run from the package root: `uv run python scripts/<script>.py`.
