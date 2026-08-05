# Methodology

This section details the deterministic mathematics behind each of the six
mission modules.

## Key escrow and recovery

The ATAC key is escrowed using **Shamir's secret-sharing scheme** over the
finite field $\mathrm{GF}(p)$ with $p = 2^{61} - 1$. A random polynomial

$$f(x) = a_0 + a_1 x + \cdots + a_{k-1} x^{k-1} \pmod{p}$$

is sampled with constant term $a_0$ equal to the key; each of $n$ custodians
receives a distinct point $(x_i, f(x_i))$. Any $k$ points reconstruct the
polynomial — and hence the key — by Lagrange interpolation:

$$f(x) = \sum_{i=1}^{k} f(x_i) \prod_{j \neq i} \frac{x - x_j}{x_i - x_j} \pmod{p},$$

while fewer than $k$ shares reveal nothing about the key. The mission uses
$n = ${{RESULT_ESCROW_SHARES}} shares and a quorum $k = ${{RESULT_ESCROW_THRESHOLD}}.

**Verification.** Each share $(x_i, y_i)$ is committed as $g^{y_i} \bmod p$
for a primitive root $g$; any party holding a claimed share can verify it
against the commitment, so a share tampered with during custody is rejected
before release.

**Custody.** Handoffs are recorded in a SHA-256 hash-chained ledger, binding
the whole custody history append-only.

**Release.** Release reconstructs the key from a verified quorum and confirms
it reproduces the escrow's key fingerprint. The recovered key is
{{RESULT_ESCROW_KEY}} (matches fingerprint: {{RESULT_RECOVERED_MATCH}}).

## Erasure-coded key recovery

To survive the loss or corruption of an individual stored fragment, the
released key is also protected by a **systematic Reed–Solomon-style erasure
code over GF(p)**. The key is treated as $k = ${{RESULT_RECOVERY_DATA_SYMBOLS}}
data symbols; a generator polynomial is evaluated at
$n = ${{RESULT_RECOVERY_CODE_SYMBOLS}} distinct field points, producing those
code symbols. Because any square Vandermonde subsystem is invertible over a
field, **any $k$ of the $n$ code symbols reconstruct the key** — the erasure
property (recovered matches original: {{RESULT_RECOVERY_MATCH}}). An integrity
checksum detects a corrupted fragment so a bad fragment never silently yields
a wrong key.

## Underwater retrieval planning

The device rests on the seabed at depth $d$ under a horizontal current
$(u, v)$. A **Haldane-style tissue model** — a set of compartments each with
half-time $t_{1/2}$ — drives the decompression schedule. Compartment pressure
relaxes exponentially toward the ambient pressure with time constant
$\tau = t_{1/2}/\ln 2$.

**Current-drift compensation.** Over a total dive time $T$, a stationary
descent bell drifts by $-T(u, v)$ relative to the seabed target. The bell
therefore starts at offset $(T u, T v)$ upstream. The planned wreck depth is
{{RESULT_WRECK_DEPTH}} m; total dive time {{RESULT_DIVE_TOTAL_S}} s yields a
surface offset of ({{RESULT_SURFACE_OFFSET_E}}, {{RESULT_SURFACE_OFFSET_N}}) m
(within tolerance: {{RESULT_TARGET_REACHABLE}}).

**Decompression ceiling.** Each compartment has an M-value ceiling; the
no-decompression bottom time is the exposure at which the limiting compartment
first saturates to its ceiling. The ascent is staged in fixed-depth steps so
no compartment violates its ceiling.

## Greek-island insertion routing

The Ionian islands are modelled as a **weighted undirected graph** with fixed
node positions; each edge carries a distance (nm) and a risk weight. Routing
finds the minimum-*cost* path, where edge cost blends distance and risk:
$c = d + \lambda r$ with a configurable risk penalty $\lambda$. The planner
uses **Dijkstra's algorithm** (or A* with a straight-line admissible
heuristic), returning the same optimum deterministically.

The canonical insertion route is {{RESULT_ROUTE}} — {{RESULT_ROUTE_HOPS}} hops,
{{RESULT_ROUTE_DISTANCE}} nm, total cost {{RESULT_ROUTE_COST}}.

## Fire-control targeting

The ATAC targeting-communicator directs a weapon onto a moving contact using
the classical *constant bearing, decreasing range* intercept. With target at
$p_0$ moving at velocity $v_t$ and weapon speed $v_w$, interception satisfies
$|p_0 + v_t t| = v_w t$, giving the quadratic
$(|v_t|^2 - v_w^2) t^2 + 2(p_0\cdot v_t) t + |p_0|^2 = 0$. A positive root is
the intercept time $t_i$; the weapon course is
$u = (p_0 + v_t t_i)/(v_w t_i)$, whose angular offset from the line of sight is
the **lead angle**. For the canonical engagement the intercept is
feasible ({{RESULT_FIRE_FEASIBLE}}) at $t_i = ${{RESULT_FIRE_INTERCEPT_S}} s with a
lead angle of {{RESULT_FIRE_LEAD_DEG}}°; where interception is impossible the
module reports the closest-approach distance instead
({{RESULT_FIRE_CLOSEST_M}} m).

## Underwater acoustic link budget

The recovered device uplinks targeting data acoustically to a surface relay.
**Transmission loss** combines geometric spreading with frequency-dependent
absorption via **Thorp's formula** (dB/km). Received SNR is
$\text{SNR} = \text{SL} - \text{TL} - \text{NL} + \text{DI}$ and the link
*closes* when SNR exceeds the detection threshold. The maximum range is found
by deterministic bisection. At the {{RESULT_LINK_RANGE_M}}-m operating range
the received SNR is {{RESULT_LINK_SNR_DB}} dB (link closes:
{{RESULT_LINK_CLOSES}}), with a maximum acoustic range of
{{RESULT_LINK_MAX_RANGE_M}} m.
