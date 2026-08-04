# Experimental Setup

## Configuration

The mission is configured declaratively in `manuscript/config.yaml` and read
by `src/for_your_eyes_only/manuscript_variables.py`. The canonical escrow uses
threshold {{RESULT_ESCROW_THRESHOLD}} of {{RESULT_ESCROW_SHARES}} shares; the
underwater profile targets a wreck depth of {{RESULT_WRECK_DEPTH}} m; routing
spans the Ionian island graph from the staging base to the wreck site
(origin–destination pair yields the route {{RESULT_ROUTE}}).

## Software environment

* Python version: {{PYTHON_VERSION}}
* Mission package: {{BOND_IDENTITY}} ({{BOND_CODENAME}}), version
  {{BOND_VERSION}}
* Title: {{BOND_TITLE}}
* Keywords ({{CONFIG_NUM_KEYWORDS}}): {{CONFIG_KEYWORDS}}
* Generated: {{GENERATION_TIMESTAMP}}

All computations are deterministic: fixed seeds, no untracked random draws, no
wall-clock dependence in persisted artifacts.
