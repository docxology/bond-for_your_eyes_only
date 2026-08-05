"""Underwater acoustic link budget for the ATAC target-communications.

The recovered ATAC device must uplink target data acoustically from depth to
a surface relay. This module models the underwater acoustic channel and
computes the deterministic link budget: path loss, received signal-to-noise
ratio, and the maximum range at which the link closes.

Real models behind the code:

* **Transmission loss** — geometric spreading plus frequency-dependent
  absorption. Spherical spreading contributes ``20 * log10(r)`` dB; absorption
  follows **Thorp's formula**, giving absorption in dB/km from the carrier
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
    "AcousticLink",
    "LinkBudget",
    "noise_level",
    "thorp_absorption",
    "transmission_loss",
    "received_snr",
]

#: Spreading coefficient (2 = spherical point-source spreading).
SPREADING = 2.0


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

    ``20*spreading*log10(range_m)`` geometric spreading plus
    ``absorption(dB/km) * range_km`` absorption.
    """
    if range_m <= 0:
        raise ValueError("range must be > 0 m")
    if spreading <= 0:
        raise ValueError("spreading must be positive")
    range_km = range_m / 1000.0
    geometric = 20.0 * spreading * math.log10(range_m)
    absorption = thorp_absorption(frequency_khz) * range_km
    return geometric + absorption


def noise_level(sea_state: float = 1.0) -> float:
    """Return a deterministic ambient sea noise level (dB re 1 uPa).

    A simple, smooth model of ambient noise growing with sea state (typical
    values run ~55-75 dB for mild seas at mid frequencies).
    """
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


@dataclass(frozen=True)
class LinkBudget:
    """The computed link budget at a given range and its closure status."""

    range_m: float
    frequency_khz: float
    transmission_loss_db: float
    received_snr_db: float
    closes: bool
    max_range_m: float

    @property
    def margin_db(self) -> float:
        """Received SNR above the detection threshold (share with threshold)."""
        return self.received_snr_db


def received_snr(link: AcousticLink, range_m: float) -> float:
    """Return the received SNR (dB) at ``range_m`` under the link config.

    ``SNR = SL - TL - NL + DI``.
    """
    tl = transmission_loss(range_m, link.frequency_khz, spreading=link.spreading)
    return link.source_level_db - tl - link.noise_level_db + link.directivity_index_db


def max_link_range(link: AcousticLink, *, lo: float = 10.0, hi: float = 200_000.0) -> float:
    """Return the maximum range (m) at which the link closes, by bisection.

    The received SNR falls monotonically with range, so the closure point is
    the unique root of ``received_snr(r) - detection_threshold = 0`` over a
    log-scaled bracket. Deterministic and bounded.
    """
    f_lo = received_snr(link, lo) - link.detection_threshold_db
    f_hi = received_snr(link, hi) - link.detection_threshold_db
    # If it doesn't even close at lo, the link never closes in this window.
    if f_lo < 0:
        return lo
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
    )
