# Experimental Setup

## Configuration

The mission is configured declaratively in `manuscript/config.yaml` and read
by `src/for_your_eyes_only/manuscript_variables.py`. The canonical escrow uses
threshold {{RESULT_ESCROW_THRESHOLD}} of {{RESULT_ESCROW_SHARES}} shares; the
key is further erasure-coded as {{RESULT_RECOVERY_DATA_SYMBOLS}} data symbols
into {{RESULT_RECOVERY_CODE_SYMBOLS}} fragments. The underwater profile targets
a wreck depth of {{RESULT_WRECK_DEPTH}} m, routing spans the Ionian island
graph to the wreck site (route {{RESULT_ROUTE}}), and the acoustic uplink runs
at {{RESULT_LINK_RANGE_M}} m.

## Software environment

* Python version: {{PYTHON_VERSION}}
* Mission package: {{BOND_IDENTITY}} ({{BOND_CODENAME}}), version
  {{BOND_VERSION}}
* Title: {{BOND_TITLE}}
* Keywords ({{CONFIG_NUM_KEYWORDS}}): {{CONFIG_KEYWORDS}}
* Source date (deterministic build stamp, not the time of rendering):
  {{SOURCE_DATE}}

All computations are deterministic: fixed seeds, no untracked random draws, no
wall-clock dependence in persisted artifacts. The stamp above is the declared
`paper.date` (or `SOURCE_DATE_EPOCH` when set), so re-rendering this section
tomorrow produces the same bytes; it deliberately does not report when the
render happened, because that value cannot be both honest and reproducible.
