"""Underwater acoustic link budget for the ATAC target-communications.

The recovered ATAC device must uplink target data acoustically from depth to
a surface relay. This module models the underwater acoustic channel and
computes the deterministic link budget: path loss, received signal-to-noise
ratio, and the maximum range at which the link closes.

Real models behind the code:

* **Transmission loss** — geometric spreading plus frequency-dependent
  absorption. Following Urick's convention the geometric term is
  ``10 * n * log10(r)`` for a spreading *exponent* ``n``: ``n = 2`` is spherical
  (``20 * log10(r)``), ``n = 1`` is cylindrical (``10 * log10(r)``), and
  ``n = 1.5`` is the common practical intermediate. Absorption follows
  **Thorp's formula**, giving absorption in dB/km from the carrier
  frequency (kHz):
  ``alpha = 0.11 f^2/(1+f^2) + 44 f^2/(4100+f^2) + 2.75e-4 f^2 + 0.003``.
* **Link budget** — received SNR in dB: ``SNR = SL - TL - NL + DI`` (source
  level minus transmission loss minus ambient noise level plus the receiver
  directivity index). The link *closes* when :code:`SNR >= DT`, the detection
  threshold.
* **Maximum range** — the range at which :code:`SNR = DT`, solved by a
  deterministic bounded bisection over the range axis (log-monotone), so the
  mission knows the acoustic coverage radius at the operating depth.

Everything is deterministic: the channel constants are fixed and the
computation is arithmetic (no RNG, no wall clock).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "CYLINDRICAL_SPREADING",
    "SPHERICAL_SPREADING",
    "SPREADING",
    "AcousticLink",
    "LinkBudget",
    "compute_link_budget",
    "max_link_range",
    "noise_level",
    "received_snr",
    "thorp_absorption",
    "transmission_loss",
]

#: Geometric spreading *exponent* ``n`` in ``10 * n * log10(r)``.
#: ``2.0`` = spherical point-source spreading (20*log10 r), ``1.0`` =
#: cylindrical waveguide spreading (10*log10 r).
SPREADING = 2.0
#: Named spreading exponents, so a caller can say what it means rather than
#: passing a bare float that a comment has to explain.
SPHERICAL_SPREADING = 2.0
CYLINDRICAL_SPREADING = 1.0


def thorp_absorption(frequency_khz: float) -> float:
    """Return Thorp absorption (dB/km) at a carrier frequency in kHz.

    Thorp's low-frequency empirical formula for sea-water absorption. Note the
    unit: dB per kilometre — convert with range in km when computing path loss.
    """
    if frequency_khz <= 0:
        raise ValueError("frequency must be > 0 kHz")
    f2 = frequency_khz * frequency_khz
    return 0.11 * f2 / (1.0 + f2) + 44.0 * f2 / (4100.0 + f2) + 2.75e-4 * f2 + 0.003


def transmission_loss(range_m: float, frequency_khz: float, *, spreading: float = SPREADING) -> float:
    """Return geometric + absorption path loss (dB) over ``range_m``.

    ``10*spreading*log10(range_m)`` geometric spreading plus
    ``absorption(dB/km) * range_km`` absorption, where ``spreading`` is the
    spreading *exponent* (2 spherical, 1 cylindrical, 1.5 practical). A decade
    of range therefore costs exactly ``10*spreading`` dB of geometric loss.
    """
    if range_m <= 0:
        raise ValueError("range must be > 0 m")
    if spreading <= 0:
        raise ValueError("spreading must be positive")
    range_km = range_m / 1000.0
    geometric = 10.0 * spreading * math.log10(range_m)
    absorption = thorp_absorption(frequency_khz) * range_km
    return geometric + absorption


def noise_level(sea_state: float = 1.0) -> float:
    """Return a deterministic ambient sea noise level (dB re 1 uPa).

    The form :math:`55 + 12\\log_{10}(1 + \\mathrm{sea\\,state})` is an
    **illustrative monotone stand-in** for the way ambient noise grows with
    sea state — it is not a published curve, and in particular it is not a
    reproduction of Wenz's sea-state spectra (cited as
    ``wenz1962noise`` in ``manuscript/references.bib``). It is a smooth
    function of the same shape used to keep the ``NL`` term of the sonar
    equation a computed quantity with a stated sea state behind it.

    This is the producer of :attr:`AcousticLink.noise_level_db`: the mission's
    link is built as ``noise_level(ATAC_SEA_STATE)`` rather than carrying a
    hand-typed dB literal, so the ``NL`` term of the sonar equation is a
    computed quantity with a stated sea state behind it.
    """
    if sea_state < 0:
        raise ValueError("sea_state must be >= 0")
    return 55.0 + 12.0 * math.log10(1.0 + sea_state)


@dataclass(frozen=True)
class AcousticLink:
    """A deterministic underwater acoustic link configuration."""

    frequency_khz: float = 15.0
    source_level_db: float = 130.0
    noise_level_db: float = 60.0
    directivity_index_db: float = 10.0
    detection_threshold_db: float = 15.0
    spreading: float = SPREADING

    def __post_init__(self) -> None:
        if self.frequency_khz <= 0:
            raise ValueError("frequency must be > 0 kHz")
        if self.source_level_db <= 0:
            raise ValueError("source_level_db must be positive")
        if self.spreading <= 0:
            raise ValueError("spreading must be positive")
        # Guard against silent NaN/inf propagation: a non-finite knob would
        # otherwise flow through Thorp absorption, spreading loss, and the
        # bisection into a budget that looks plausible but is garbage.
        for field in (
            "frequency_khz",
            "source_level_db",
            "noise_level_db",
            "directivity_index_db",
            "detection_threshold_db",
            "spreading",
        ):
            if not math.isfinite(getattr(self, field)):
                raise ValueError(f"{field} must be finite")


@dataclass(frozen=True)
class LinkBudget:
    """The computed link budget at a given range and its closure status.

    ``detection_threshold_db`` is carried alongside the received SNR so the
    budget is self-describing: :attr:`margin_db` is a real margin rather than a
    restatement of the SNR, and ``closes`` can be re-derived by any consumer.
    """

    range_m: float
    frequency_khz: float
    transmission_loss_db: float
    received_snr_db: float
    closes: bool
    max_range_m: float
    detection_threshold_db: float

    @property
    def margin_db(self) -> float:
        """Received SNR *above* the detection threshold (negative when short).

        This is the operationally meaningful quantity: how much signal the link
        has in hand beyond the threshold at which the receiver can detect it.
        ``closes`` is exactly ``margin_db >= 0``.
        """
        return self.received_snr_db - self.detection_threshold_db


def received_snr(link: AcousticLink, range_m: float) -> float:
    """Return the received SNR (dB) at ``range_m`` under the link config.

    ``SNR = SL - TL - NL + DI``.
    """
    tl = transmission_loss(range_m, link.frequency_khz, spreading=link.spreading)
    return link.source_level_db - tl - link.noise_level_db + link.directivity_index_db


def max_link_range(link: AcousticLink, *, lo: float = 10.0, hi: float = 200_000.0) -> float:
    """Return the maximum range (m) at which the link closes, by bisection.

    The received SNR falls monotonically with range, so the closure point is
    the unique root of ``received_snr(r) - detection_threshold = 0`` over the
    bracket ``[lo, hi]``. Deterministic and bounded.

    Bracket endpoints are reported honestly rather than as a closure range:

    * if the link already fails at ``lo`` it never closes anywhere in the
      window, so the coverage radius is ``0.0`` — reporting ``lo`` would claim
      coverage the link does not have;
    * if it still closes at ``hi`` the true root lies beyond the bracket, so
      ``hi`` is returned as a lower bound on the coverage radius.

    ``lo`` and ``hi`` must satisfy ``0 < lo < hi``; a degenerate or inverted
    bracket is rejected rather than silently returning a wrong radius.
    """
    if not (0.0 < lo < hi):
        raise ValueError("need 0 < lo < hi for the bisection bracket")
    f_lo = received_snr(link, lo) - link.detection_threshold_db
    f_hi = received_snr(link, hi) - link.detection_threshold_db
    if f_lo < 0:
        return 0.0
    if f_hi > 0:
        return hi
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        f_mid = received_snr(link, mid) - link.detection_threshold_db
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def compute_link_budget(link: AcousticLink, range_m: float) -> LinkBudget:
    """Compute the full link budget at ``range_m`` for ``link``.

    Returns the path loss, received SNR, whether the link closes (SNR >= DT),
    and the global maximum range for the link.
    """
    if range_m <= 0:
        raise ValueError("range must be > 0 m")
    tl = transmission_loss(range_m, link.frequency_khz, spreading=link.spreading)
    snr = received_snr(link, range_m)
    closes = snr >= link.detection_threshold_db
    return LinkBudget(
        range_m=range_m,
        frequency_khz=link.frequency_khz,
        transmission_loss_db=tl,
        received_snr_db=snr,
        closes=closes,
        max_range_m=max_link_range(link),
        detection_threshold_db=link.detection_threshold_db,
    )
