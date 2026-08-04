# Introduction

The ATAC (Automatic Targeting Attack Communicator) is a lost-key device whose
recovery demands coordinated custody, underwater access, and insertion
planning. For Your Eyes Only (1981) frames the operational scenario; this
package implements the mission mathematics as reproducible, deterministic
software in the PROJECT BOND film suite.

The three domain modules form the core of the mission:

* `key_escrow` — escrow/recovery protocol for the ATAC lost key: custody,
  verification, and quorum release.
* `underwater_retrieval` — planning the sea-based recovery of the device from
  the wreck, compensating for depth and currents.
* `island_routing` — Greek-island insertion routing from the staging base to
  the wreck's vicinity.

A shared, frozen protocol (BOND-API) defines the mission lifecycle — brief,
recon, plan, execute, debrief — and the `mission` module adapts the pure
domain mathematics to that contract, registering the suite's gadgets for
orchestration. This separation keeps the mathematics infrastructure-free and
importable without the protocol, while the adapter makes the mission
discoverable by the broader BOND orchestrator.

## Reader's guide

* §2 describes the mathematical methods behind each domain module.
* §3 presents the computed mission results and figures.
* §5 details the experimental configuration; §6 the reproducibility contract.
