# Results

The mission was executed end to end through the frozen protocol; all results
below are computed live by the domain modules (never hand-authored).

## Escrow release

A quorum of {{RESULT_ESCROW_THRESHOLD}} of {{RESULT_ESCROW_SHARES}} custodians
releases the key deterministically. The reconstructed key is
{{RESULT_ESCROW_KEY}}, confirmed to match the escrow fingerprint
({{RESULT_RECOVERED_MATCH}}). A smaller quorum is rejected, and a tampered
share fails verification before release.

## Underwater retrieval

The retrieval dive to {{RESULT_WRECK_DEPTH}} m completes in
{{RESULT_DIVE_TOTAL_S}} s of deterministic profile time. The surface drift
offset is ({{RESULT_SURFACE_OFFSET_E}}, {{RESULT_SURFACE_OFFSET_N}}) m; the
target is reachable within the operational envelope
({{RESULT_TARGET_REACHABLE}}). The depth-time profile is shown in
Figure {@fig:dive_profile}.

![ATAC underwater retrieval dive profile](dive_profile.png){#fig:dive_profile}

## Island insertion routing

The least-cost insertion route from the staging base to the wreck site is
{{RESULT_ROUTE}} ({{RESULT_ROUTE_HOPS}} hops, {{RESULT_ROUTE_DISTANCE}} nm,
cost {{RESULT_ROUTE_COST}}). The route cost intentionally blends distance and
risk, favouring safe passages without abandoning the shortest corridor. The
Ionian graph and planned route are shown in Figure {@fig:island_graph}.

![ATAC Ionian insertion route](island_graph.png){#fig:island_graph}
