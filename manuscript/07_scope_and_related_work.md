# Scope and Related Work

## Scope

This package implements the deterministic mission mathematics for the ATAC
recovery scenario. It covers key escrow/recovery, underwater retrieval
planning, and island insertion routing. It does not attempt to model the
physical dynamics of a real diving operation beyond the closed-form Haldane
saturation and ballistic drift used here; it is mission-planning software, not
a training simulator.

## Related work

* **Secret sharing** — Shamir's threshold scheme (1979) is the canonical
  construction for splitting a secret among parties such that a quorum can
  reconstruct it. Our implementation uses Lagrange interpolation over a
  Mersenne-prime field with deterministic share generation.
* **Decompression modelling** — Haldane-style multi-compartment tissue models
  underpin recreational and technical dive planning; our staged-ascent
  scheduler applies the same exponential-saturation principle deterministically.
* **Shortest path routing** — Dijkstra's algorithm and A* (with an admissible
  heuristic) are the standard tools for weighted-graph route planning; our
  Ionian insertion graph blends distance and risk into a single scalar cost.

## Limitations

The graph topology and positions are stylised (nominal nautical-mile grid, not
survey-grade chart data). The decompression model is a simplified classroom
model and is not certified for live diving. These simplifications keep the
mission fully deterministic and testable while preserving the mathematical
substance of each concept.
