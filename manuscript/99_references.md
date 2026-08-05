# References

Every entry below corresponds to a key in `references.bib`, and every key is
cited from the numbered prose — both directions are enforced by
`tests/test_manuscript_crossrefs.py`, so an uncited entry or an undefined
citation fails the suite. Each is cited because this package implements the
model it describes, not to decorate the bibliography.

What the tests cannot check is whether each entry is a real publication with
the details given; that was verified by hand, and one entry was found wrong and
corrected (see *Decompression modelling* below). Treat the bibliographic
details as human-verified, not machine-verified.

## Secret sharing and key escrow

- Shamir, A. (1979). How to share a secret. *Communications of the ACM*,
  22(11), 612–613. — The threshold scheme implemented in `key_escrow.py`:
  polynomial interpolation over a finite field, any `k` of `n` shares
  reconstructing the secret.
- Blakley, G. R. (1979). Safeguarding cryptographic keys. *Proceedings of the
  AFIPS National Computer Conference*, 48, 313–317. — The independent
  co-discovery of threshold secret sharing in the same year, via intersecting
  hyperplanes rather than polynomial interpolation.

## Erasure coding

- Reed, I. S., & Solomon, G. (1960). Polynomial codes over certain finite
  fields. *Journal of the Society for Industrial and Applied Mathematics*,
  8(2), 300–304. — The systematic polynomial code whose evaluation and
  interpolation structure `key_recovery.py` realises as a Vandermonde system
  over GF(p).
- Berlekamp, E. R. (1968). *Algebraic Coding Theory*. McGraw-Hill. — The
  standard treatment of the algebraic decoding problem underlying
  any-`k`-of-`n` erasure recovery.

## Decompression modelling

- Boycott, A. E., Damant, G. C. C., & Haldane, J. S. (1908). The prevention of
  compressed-air illness. *The Journal of Hygiene*, 8(3), 342–443. — The
  compartmental exponential-saturation model behind
  `underwater_retrieval.HaldaneModel`. (Earlier drafts of this bibliography
  cited "Haldane, J. S. (1908), The relation of the action of carbonic oxide to
  oxygen tension, *Journal of Physiology*, 37, 355" for this model. That entry
  was wrong twice over: its bibliographic details did not match any Haldane
  paper, and the carbon-monoxide work it half-named contains no decompression
  model. This is the paper the model actually comes from.)
- Bühlmann, A. A. (1984). *Decompression–Decompression Sickness*.
  Springer-Verlag, Berlin. — The modern multi-compartment formulation with
  M-value ceilings that the staged-ascent scheduler follows in principle.

## Shortest-path routing

- Dijkstra, E. W. (1959). A note on two problems in connexion with graphs.
  *Numerische Mathematik*, 1, 269–271. — The non-negative-weight shortest-path
  algorithm used by `island_routing.plan_route`.
- Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the
  heuristic determination of minimum cost paths. *IEEE Transactions on Systems
  Science and Cybernetics*, 4(2), 100–107. — A\* and the admissibility
  condition that lets the straight-line heuristic prune without changing the
  optimum.

## Underwater acoustics

- Thorp, W. H. (1967). Analytic description of the low-frequency attenuation
  coefficient. *The Journal of the Acoustical Society of America*, 42(1), 270. —
  The empirical sea-water absorption formula implemented in
  `acoustic_link.thorp_absorption`.
- Urick, R. J. (1983). *Principles of Underwater Sound* (3rd ed.).
  McGraw-Hill. — The sonar equation `SNR = SL − TL − NL + DI` and the detection
  threshold convention used throughout the link budget.

## Fire control

The constant-bearing intercept solved in `targeting.py` is classical pursuit
geometry with a closed-form quadratic solution — standard textbook material
rather than the contribution of a single citable paper, so no reference is
claimed for it here rather than attaching a plausible-looking one.
