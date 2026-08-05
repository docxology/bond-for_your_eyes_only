"""for_your_eyes_only — ATAC special-agent mission software.

For Your Eyes Only (1981), mission codename **ATAC**: recovery of the lost
targeting-communicator device. This package is a BOND-suite film implementing
the frozen :class:`bond_api.protocol.MissionProvider` protocol while keeping
its pure domain mathematics infrastructure-free.

Domain modules (pure, importable without bond-api):

* :mod:`key_escrow` — ATAC lost-key escrow/recovery: custody, verification,
  release (Shamir secret sharing over a finite field + custody chain).
* :mod:`key_recovery` — erasure-coded lost-key recovery (Vandermonde /
  Reed–Solomon-style) over GF(p), so fragments survive loss or corruption.
* :mod:`underwater_retrieval` — underwater retrieval planning: depth profile,
  current-drift compensation, Haldane-style decompression scheduling.
* :mod:`island_routing` — Greek-island insertion routing (Dijkstra / A*).
* :mod:`targeting` — fire-control intercept lead-angle firing solution.
* :mod:`acoustic_link` — underwater acoustic link budget (Thorp absorption,
  SNR, maximum range).

:mod:`mission` is the thin adapter that wraps these domain modules in the
frozen protocol and registers the suite's gadgets with the
:class:`bond_api.registry.GadgetRegistry`.
"""

from __future__ import annotations

__version__ = "0.1.0"

from for_your_eyes_only import (
    acoustic_link,
    island_routing,
    key_escrow,
    key_recovery,
    targeting,
    underwater_retrieval,
)

__all__ = [
    "__version__",
    "acoustic_link",
    "island_routing",
    "key_escrow",
    "key_recovery",
    "targeting",
    "underwater_retrieval",
]
