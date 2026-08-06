# Results

The mission was executed end to end through the frozen protocol; all results
below are computed live by the domain modules (never hand-authored).

| Stage | Result |
|---|---|
| Escrow release | quorum {{RESULT_ESCROW_THRESHOLD}}-of-{{RESULT_ESCROW_SHARES}} · key {{RESULT_ESCROW_KEY}} · fingerprint match {{RESULT_RECOVERED_MATCH}} · custody {{RESULT_CUSTODY_OK}} ({{RESULT_CUSTODY_LEN}}-record chain) |
| Erasure-coded recovery | {{RESULT_RECOVERY_DATA_SYMBOLS}}-of-{{RESULT_RECOVERY_CODE_SYMBOLS}} · recovered match {{RESULT_RECOVERY_MATCH}} |
| Underwater retrieval | {{RESULT_WRECK_DEPTH}} m · {{RESULT_DIVE_BOTTOM_S}} s bottom · {{RESULT_DIVE_STOPS}} decompression stops · {{RESULT_DIVE_TOTAL_S}} s total · surface offset ({{RESULT_SURFACE_OFFSET_E}}, {{RESULT_SURFACE_OFFSET_N}}) m · reachable {{RESULT_TARGET_REACHABLE}} |
| Island routing | {{RESULT_ROUTE}} · {{RESULT_ROUTE_HOPS}} hops · {{RESULT_ROUTE_DISTANCE}} nm · cost {{RESULT_ROUTE_COST}} |
| Fire control | feasible {{RESULT_FIRE_FEASIBLE}} · intercept {{RESULT_FIRE_INTERCEPT_S}} s · lead {{RESULT_FIRE_LEAD_DEG}}° · closest-approach {{RESULT_FIRE_CLOSEST_M}} m |
| Acoustic link | SNR {{RESULT_LINK_SNR_DB}} dB at {{RESULT_LINK_RANGE_M}} m · TL {{RESULT_LINK_TL_DB}} dB · threshold {{RESULT_LINK_THRESHOLD_DB}} dB · margin {{RESULT_LINK_MARGIN_DB}} dB · max range {{RESULT_LINK_MAX_RANGE_M}} m · closes {{RESULT_LINK_CLOSES}} |

## Escrow release

A quorum of {{RESULT_ESCROW_THRESHOLD}} of {{RESULT_ESCROW_SHARES}} custodians
releases the key deterministically. The reconstructed key is
{{RESULT_ESCROW_KEY}}, confirmed to match the escrow fingerprint
({{RESULT_RECOVERED_MATCH}}). A smaller quorum is rejected, and a tampered
share fails verification before release.

Custody is an audited concern here, not decoration: the escrow carries a
{{RESULT_CUSTODY_LEN}}-record SHA-256 hash-chained ledger of the handoffs, whose
well-formedness is recomputed ({{RESULT_CUSTODY_OK}}) and whose tip hash is
{{RESULT_CUSTODY_TIP}}.

That confirmation is *re-derived*, not asserted: the SHA-256 fingerprint of the
released key is recomputed and compared against the one the escrow stored. This
matters because the preflight check treats the same value as a pass/fail
verdict — had it been a stapled literal, the verdict could never have failed
and would have reported success regardless of what release returned.

## Erasure-coded key recovery

The released key is encoded as {{RESULT_RECOVERY_DATA_SYMBOLS}} data symbols
into {{RESULT_RECOVERY_CODE_SYMBOLS}} code fragments over GF(p). Any
{{RESULT_RECOVERY_DATA_SYMBOLS}} fragments recover the key (recovered matches
original: {{RESULT_RECOVERY_MATCH}}), and a corrupted fragment is detected by
the integrity checksum before it can yield a wrong key.

The any-`k` claim is tested as stated rather than in its easy form: the decoder
takes an explicit set of surviving fragment positions, and the test suite
enumerates *every* combination of surviving fragments — including sets that
contain none of the leading ones — and requires each to reconstruct the key.
Requesting checksum verification when no checksum symbol is present is an
error rather than a silent skip, so a caller asking to be protected is never
told that nothing was wrong.

## Underwater retrieval

The retrieval dive to {{RESULT_WRECK_DEPTH}} m completes in
{{RESULT_DIVE_TOTAL_S}} s of deterministic profile time: a
{{RESULT_DIVE_BOTTOM_S}} s bottom exposure followed by
{{RESULT_DIVE_STOPS}} decompression stops totaling {{RESULT_DIVE_ASCENT_S}} s
of ascent, each stop sized from the compartment ceilings (see §2). The surface
drift offset is ({{RESULT_SURFACE_OFFSET_E}}, {{RESULT_SURFACE_OFFSET_N}}) m;
the target is reachable within the operational envelope
({{RESULT_TARGET_REACHABLE}}). The depth-time profile is shown in
Figure [@fig:dive_profile].

![ATAC underwater retrieval dive profile](dive_profile.png){#fig:dive_profile}

## Island insertion routing

The least-cost insertion route from the staging base to the wreck site is
{{RESULT_ROUTE}} ({{RESULT_ROUTE_HOPS}} hops, {{RESULT_ROUTE_DISTANCE}} nm,
cost {{RESULT_ROUTE_COST}}). The route cost blends distance and risk, but on
this graph that blend never changes the answer: for all 28 node pairs the route
chosen at risk weight 0 is the route chosen at risk weight 50, because the
Ionian island chain's safest corridor is also its shortest. The reported route
is therefore the shortest route, and this section claims nothing more for it.
The risk term is exercised as a mechanism on a purpose-built two-option graph
in the test suite, not here. The Ionian graph and planned route are shown in
Figure [@fig:island_graph].

![ATAC Ionian insertion route](island_graph.png){#fig:island_graph}

## Targeting solution

The ATAC fire-control solution for the canonical contact is feasible
({{RESULT_FIRE_FEASIBLE}}) with an intercept time of {{RESULT_FIRE_INTERCEPT_S}}
s, a lead angle of {{RESULT_FIRE_LEAD_DEG}}° and a weapon course of
{{RESULT_FIRE_COURSE_DEG}}°; where a close is not achievable, the module
reports the closest-approach distance ({{RESULT_FIRE_CLOSEST_M}} m). The
intercept geometry is shown in Figure [@fig:targeting_geometry].

![ATAC targeting intercept geometry](targeting_geometry.png){#fig:targeting_geometry}

## Acoustic link budget

At the {{RESULT_LINK_RANGE_M}}-m operating range the ATAC uplink receives
{{RESULT_LINK_SNR_DB}} dB (path loss {{RESULT_LINK_TL_DB}} dB) against a
{{RESULT_LINK_THRESHOLD_DB}} dB detection threshold, leaving a margin of
{{RESULT_LINK_MARGIN_DB}} dB; the link closes ({{RESULT_LINK_CLOSES}}) with a
maximum acoustic range of {{RESULT_LINK_MAX_RANGE_M}} m. Because the operating
range sits inside that maximum, the uplink is not run at the edge of its
budget. The SNR-vs-range curve is shown in Figure [@fig:acoustic_link].

![ATAC underwater acoustic link budget](acoustic_link.png){#fig:acoustic_link}
