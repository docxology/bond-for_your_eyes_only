# Methodology

This section details the deterministic mathematics behind each of the three
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
it reproduces the escrow's key fingerprint. With the canonical key the
recovered value is {{RESULT_ESCROW_KEY}} (matches fingerprint:
{{RESULT_RECOVERED_MATCH}}).

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
