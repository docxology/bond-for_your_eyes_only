# Scope and Related Work

## Scope

This package implements the deterministic mission mathematics for the ATAC
recovery scenario. It covers key escrow/recovery (including erasure-coded
reconstruction), underwater retrieval planning, island insertion routing,
fire-control targeting, and underwater acoustic link budgeting. It does not
attempt to model the physical dynamics of a real diving operation beyond the
closed-form Haldane saturation and ballistic drift used here; it is
mission-planning software, not a training simulator.

## Related work

* **Secret sharing** — Shamir's threshold scheme (1979) is the canonical
  construction for splitting a secret among parties such that a quorum can
  reconstruct it. Our implementation uses Lagrange interpolation over a
  Mersenne-prime field with deterministic share generation.
* **Erasure coding** — Reed and Solomon (1960) introduced the systematic
  polynomial code; our Vandermonde system over GF(p) realises the same
  any-`k`-of-`n` recovery property with an integrity checksum.
* **Decompression modelling** — Haldane-style multi-compartment tissue models
  underpin recreational and technical dive planning; our staged-ascent
  scheduler applies the same exponential-saturation principle deterministically.
* **Shortest path routing** — Dijkstra's algorithm and A* (with an admissible
  heuristic) are the standard tools for weighted-graph route planning; our
  Ionian insertion graph blends distance and risk into a single scalar cost.
* **Pursuit interception** — the constant-bearing intercept problem has a
  closed-form quadratic solution (see e.g. ballistics/fire-control texts); our
  lead-angle computation follows that classic geometry.
* **Underwater acoustics** — Thorp's absorption model and the sonar-equation
  link budget (source level, transmission loss, noise, directivity) are
  standard in underwater acoustic channel analysis.

## Limitations

The graph topology and positions are stylised (nominal nautical-mile grid, not
survey-grade chart data). The decompression staging couples to the tissue model
but uses classroom-grade proportional M-value ceilings rather than a
field-validated Bühlmann line, and the acoustic ambient-noise term is a smooth
monotone stand-in for sea-state noise, not a reproduction of Wenz's spectra;
neither is certified for live operations. The custody chain models a nominal
sequence of handoffs over the escrow's custodians — the audit *mechanism* is
real (SHA-256 hash chaining, recomputed consistency), but the handoffs
themselves are scenario fiction, not a recorded operational trail. These
simplifications keep the mission fully deterministic and testable while
preserving the mathematical substance of each concept.
