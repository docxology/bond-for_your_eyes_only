# Methodology

This section details the deterministic mathematics behind each of the six
mission modules.

## Key escrow and recovery

The ATAC key is escrowed using **Shamir's secret-sharing scheme**
[@shamir1979share] — independently co-discovered the same year by Blakley via
intersecting hyperplanes [@blakley1979safeguarding] — over the
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
{{RESULT_ESCROW_KEY}} (matches fingerprint: {{RESULT_RECOVERED_MATCH}}). The
match is obtained by recomputing $\mathrm{SHA\text{-}256}(k)$ over the released
key and comparing it to the stored fingerprint, so the reported value is a
measurement rather than a restatement of an intention.

**Key derivation.** The escrowed key is derived from the mission seed at import
time rather than written down as a literal, so there is exactly one place the
key can come from and no configuration file can claim a different one.

## Erasure-coded key recovery

To survive the loss or corruption of an individual stored fragment, the
released key is also protected by a **systematic Reed–Solomon-style erasure
code over GF(p)** [@reed1960polynomial; @berlekamp1968algebraic]. The key is treated as $k = ${{RESULT_RECOVERY_DATA_SYMBOLS}}
data symbols; a generator polynomial is evaluated at
$n = ${{RESULT_RECOVERY_CODE_SYMBOLS}} distinct field points, producing those
code symbols. Because any square Vandermonde subsystem is invertible over a
field, **any $k$ of the $n$ code symbols reconstruct the key** — the erasure
property (recovered matches original: {{RESULT_RECOVERY_MATCH}}). An integrity
checksum detects a corrupted fragment so a bad fragment never silently yields
a wrong key.

The decoder takes the positions of the surviving fragments explicitly, which is
what makes the erasure property exercisable rather than merely asserted: a
decoder hard-wired to the leading $k$ fragments would satisfy the round-trip
test while being unable to survive the loss of fragment 0. Selecting the
evaluation points $x_i$ of the actual survivors and solving that Vandermonde
subsystem is the general case.

## Underwater retrieval planning

The device rests on the seabed at depth $d$ under a horizontal current
$(u, v)$. A **Haldane-style tissue model** [@boycott1908prevention] — a set of
compartments each with half-time $t_{1/2}$ — drives the decompression schedule. Compartment pressure
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
first saturates to its ceiling,
$t_i = \tau_i \ln\frac{P_{amb}-1}{P_{amb}-M_i}$, in the multi-compartment form
of [@buhlmann1984decompression].

We state the boundary of this model plainly, because it is easy to overread.
The ascent is staged in **fixed-depth steps at a fixed rate**: the staging is
geometric and does not consult the tissue state. The tissue model computes
no-decompression limits and ceilings as an independent quantity; it does not
size the stops. A stage boundary in the reported profile is therefore not a
decompression obligation, and the profile should not be read as a
physiologically validated schedule. Wiring the ceiling into the staging is
recorded as open work rather than claimed as done.

## Greek-island insertion routing

The Ionian islands are modelled as a **weighted undirected graph** with fixed
node positions; each edge carries a distance (nm) and a risk weight. Routing
finds the minimum-*cost* path, where edge cost blends distance and risk:
$c = d + \lambda r$ with a configurable risk penalty $\lambda$. The planner
uses **Dijkstra's algorithm** [@dijkstra1959note], or A* with a straight-line
admissible heuristic [@hart1968formal], returning the same optimum
deterministically.

**What $\lambda$ does and does not do here.** Raising $\lambda$ always raises
the cost of a route, but on the shipped Ionian graph it never changes which
route is chosen: the least-distance and least-risk corridors coincide for every
one of the 28 node pairs. So this package demonstrates the *cost* blend, not
risk-driven path selection; the selection mechanism is exercised on a separate
two-option graph in the test suite. Read the canonical route below as the
shortest route, which on this graph is also the safest.

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
absorption via **Thorp's formula** (dB/km) [@thorp1967analytic]. Geometric
spreading is $10 n \log_{10} r$ for a spreading exponent $n$ — $n = 2$
spherical, $n = 1$ cylindrical — and the wreck uplink is modelled as a
shallow-water horizontal channel, so it uses $n = 1$. The ambient noise term NL
is computed from a declared sea state rather than entered as a decibel literal.
Received SNR is
$\text{SNR} = \text{SL} - \text{TL} - \text{NL} + \text{DI}$
[@urick1983principles] and the link
*closes* when SNR exceeds the detection threshold $\text{DT}$. The **margin**
is $\text{SNR} - \text{DT}$ — the signal in hand beyond the point of
detectability — so closure is exactly a non-negative margin. At the
{{RESULT_LINK_RANGE_M}}-m operating range the received SNR is
{{RESULT_LINK_SNR_DB}} dB against a {{RESULT_LINK_THRESHOLD_DB}} dB threshold,
a margin of {{RESULT_LINK_MARGIN_DB}} dB (link closes:
{{RESULT_LINK_CLOSES}}).

**Maximum range.** Since SNR falls monotonically with range, the coverage
radius is the unique root of $\text{SNR}(r) = \text{DT}$, found by bounded
bisection: {{RESULT_LINK_MAX_RANGE_M}} m. The bracket endpoints are reported
honestly — a link that already fails at the bracket floor has a coverage radius
of zero, not a coverage radius equal to the floor, and a link still closing at
the ceiling returns that ceiling as a lower bound.
