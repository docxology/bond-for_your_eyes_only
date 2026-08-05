# Introduction

The ATAC (Automatic Targeting Attack Communicator) is a lost-key device whose
recovery demands coordinated custody, underwater access, and insertion
planning, after which it must be directed onto target and communicate that
solution acoustically. For Your Eyes Only (1981) frames the operational
scenario; this package implements the mission mathematics as reproducible,
deterministic software in the PROJECT BOND film suite.

The six domain modules form the core of the mission:

* `key_escrow` — escrow/recovery of the ATAC key (Shamir custody, verification,
  quorum release).
* `key_recovery` — erasure-coded reconstruction so key fragments survive loss
  or corruption.
* `underwater_retrieval` — sea-based recovery of the device from the wreck,
  compensating for depth and currents.
* `island_routing` — Greek-island insertion routing from the staging base to
  the wreck's vicinity.
* `targeting` — fire-control intercept lead-angle firing solution.
* `acoustic_link` — underwater acoustic uplink budget for the recovered device.

A shared, frozen protocol (BOND-API) defines the mission lifecycle — brief,
recon, plan, execute, debrief — and the `mission` module adapts the pure
domain mathematics to that contract, registering the suite's gadgets for
orchestration. This separation keeps the mathematics infrastructure-free and
importable without the protocol, while the adapter makes the mission
discoverable by the broader BOND orchestrator. The mission's public protocol
surface is stable across phases; only the internal scenario deepens.

## Reader's guide

* §2 describes the mathematical methods behind each domain module.
* §3 presents the computed mission results and figures.
* §5 details the experimental configuration; §6 the reproducibility contract.
