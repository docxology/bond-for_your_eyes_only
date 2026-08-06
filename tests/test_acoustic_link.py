"""Real-data tests for the underwater acoustic link budget module."""

import pytest

from for_your_eyes_only import acoustic_link as ac


def test_thorp_absorption_positive_monotone():
    """Absorption > 0 and generally grows with frequency."""
    low = ac.thorp_absorption(1.0)
    high = ac.thorp_absorption(50.0)
    assert low > 0.0
    assert high > low


def test_thorp_absorption_validation():
    with pytest.raises(ValueError):
        ac.thorp_absorption(0.0)
    with pytest.raises(ValueError):
        ac.thorp_absorption(-1.0)


def test_transmission_loss_grows_with_range():
    lo = ac.transmission_loss(100.0, 15.0)
    hi = ac.transmission_loss(1000.0, 15.0)
    assert hi > lo


def test_transmission_loss_spreading_cylindrical_less_than_spherical():
    """Cylindrical spreading (exponent 1) gives less loss than spherical (2)."""
    cyl = ac.transmission_loss(1000.0, 15.0, spreading=ac.CYLINDRICAL_SPREADING)
    sph = ac.transmission_loss(1000.0, 15.0, spreading=ac.SPHERICAL_SPREADING)
    assert cyl < sph


def test_geometric_spreading_exponent_is_what_the_label_says():
    """Pin the exponent itself: a decade of range costs 10*n dB of spreading.

    The ordering test above passes for *any* increasing function of the
    spreading parameter — it held while the code computed 20*n*log10(r), which
    made `spreading=2.0` (labelled spherical) 40*log10(r) and `spreading=1.0`
    (labelled cylindrical) actually spherical. Subtracting the absorption term
    isolates the geometry and binds each named constant to its textbook law.
    """

    def geometric(range_m: float, spreading: float) -> float:
        absorption = ac.thorp_absorption(15.0) * range_m / 1000.0
        return ac.transmission_loss(range_m, 15.0, spreading=spreading) - absorption

    # Spherical: 20 dB per decade, and exactly 20*log10(r).
    assert geometric(10_000.0, ac.SPHERICAL_SPREADING) - geometric(1_000.0, ac.SPHERICAL_SPREADING) == pytest.approx(
        20.0
    )
    assert geometric(1_000.0, ac.SPHERICAL_SPREADING) == pytest.approx(60.0)
    # Cylindrical: 10 dB per decade, and exactly 10*log10(r).
    assert geometric(10_000.0, ac.CYLINDRICAL_SPREADING) - geometric(
        1_000.0, ac.CYLINDRICAL_SPREADING
    ) == pytest.approx(10.0)
    assert geometric(1_000.0, ac.CYLINDRICAL_SPREADING) == pytest.approx(30.0)
    # The module default is the spherical exponent.
    assert ac.SPREADING == ac.SPHERICAL_SPREADING


def test_transmission_loss_validation():
    with pytest.raises(ValueError):
        ac.transmission_loss(0.0, 15.0)
    with pytest.raises(ValueError):
        ac.transmission_loss(100.0, 15.0, spreading=0.0)


def test_noise_level_grows_with_sea_state():
    calm = ac.noise_level(0.0)
    rough = ac.noise_level(5.0)
    assert rough > calm
    with pytest.raises(ValueError):
        ac.noise_level(-1.0)


def test_mission_link_noise_is_computed_from_the_declared_sea_state():
    """`noise_level` is consumed, not decorative.

    It was previously exported and tested while nothing called it: the mission
    link carried a hand-typed 55.0 dB literal unrelated to the model. This
    binds the two, so changing the sea state moves the link budget.
    """
    from for_your_eyes_only.mission import ATAC_LINK, ATAC_SEA_STATE

    assert ATAC_LINK.noise_level_db == pytest.approx(ac.noise_level(ATAC_SEA_STATE))
    # And the binding is load-bearing: a different sea state is a different NL.
    assert ac.noise_level(ATAC_SEA_STATE + 1.0) != pytest.approx(ATAC_LINK.noise_level_db)


def test_received_snr_decreases_with_range():
    link = ac.AcousticLink()
    assert ac.received_snr(link, 100.0) > ac.received_snr(link, 10000.0)


def test_max_range_bisection_interior():
    """A tuned link has an interior (non-degenerate) max range."""
    link = ac.AcousticLink(
        frequency_khz=15.0,
        source_level_db=145.0,
        noise_level_db=55.0,
        directivity_index_db=10.0,
        detection_threshold_db=8.0,
        spreading=1.0,
    )
    max_range = ac.max_link_range(link)
    # At max_range the SNR is at (or just below) the threshold.
    assert ac.received_snr(link, max_range) <= ac.received_snr(link, max_range * 0.999)
    # max range is interior to the bisection window
    assert 100.0 < max_range < 200_000.0
    # closer range closes, farther does not
    assert ac.received_snr(link, max_range * 0.9) >= link.detection_threshold_db


def test_compute_link_budget_closure_state():
    link = ac.AcousticLink(spreading=1.0)
    budget = ac.compute_link_budget(link, 100.0)
    assert budget.closes is True
    assert budget.received_snr_db > link.detection_threshold_db
    assert budget.max_range_m > 0
    far = ac.compute_link_budget(link, 200_000.0)
    assert far.closes is False or far.received_snr_db < link.detection_threshold_db


def test_compute_link_budget_validation():
    with pytest.raises(ValueError):
        ac.compute_link_budget(ac.AcousticLink(), 0.0)


def test_link_validation():
    with pytest.raises(ValueError):
        ac.AcousticLink(frequency_khz=0.0)
    with pytest.raises(ValueError):
        ac.AcousticLink(source_level_db=0.0)
    with pytest.raises(ValueError):
        ac.AcousticLink(spreading=-1.0)


def test_canonical_mission_link_closes():
    """The mission's canonical link closes at its operating range with margin."""
    from for_your_eyes_only.mission import ATAC_LINK, ATAC_LINK_RANGE_M, canonical_mission

    sc = canonical_mission()
    assert sc.link_budget.closes is True
    # A real margin over the threshold, not merely "some positive number".
    assert sc.link_budget.received_snr_db > ATAC_LINK.detection_threshold_db
    assert sc.link_budget.margin_db > 0.0
    # operating range < max range (interior closure)
    assert ATAC_LINK_RANGE_M < sc.link_budget.max_range_m


def test_link_budget_margin_is_relative_to_threshold():
    """margin_db is SNR *above* the detection threshold, not the raw SNR."""
    link = ac.AcousticLink(spreading=1.0, detection_threshold_db=15.0)
    budget = ac.compute_link_budget(link, 500.0)
    assert budget.detection_threshold_db == 15.0
    assert budget.margin_db == pytest.approx(budget.received_snr_db - 15.0)
    # The margin must not be a restatement of the SNR (the old bug).
    assert budget.margin_db != budget.received_snr_db
    # closes is exactly "margin is non-negative".
    assert budget.closes is (budget.margin_db >= 0.0)


def test_margin_is_negative_when_link_does_not_close():
    """A link short of threshold reports a negative margin, not a positive SNR."""
    link = ac.AcousticLink(source_level_db=100.0, detection_threshold_db=40.0)
    budget = ac.compute_link_budget(link, 50_000.0)
    assert budget.closes is False
    assert budget.margin_db < 0.0


def test_max_link_range_reports_zero_when_link_never_closes():
    """A link failing at the bracket floor has no coverage — not `lo` metres of it."""
    link = ac.AcousticLink(source_level_db=1.0, detection_threshold_db=200.0)
    assert ac.received_snr(link, 10.0) < link.detection_threshold_db
    assert ac.max_link_range(link) == 0.0
    assert ac.compute_link_budget(link, 10.0).max_range_m == 0.0


def test_max_link_range_returns_bracket_ceiling_when_still_closing():
    """When the root lies beyond the bracket, `hi` is returned as a lower bound."""
    link = ac.AcousticLink(source_level_db=10_000.0, detection_threshold_db=0.0)
    assert ac.max_link_range(link, lo=10.0, hi=5_000.0) == 5_000.0


def test_link_rejects_nonfinite_fields():
    """NaN/inf must not flow silently through the budget (defensive hardening)."""
    import math as _math

    with pytest.raises(ValueError):
        ac.AcousticLink(detection_threshold_db=_math.nan)
    with pytest.raises(ValueError):
        ac.AcousticLink(frequency_khz=_math.inf)
    with pytest.raises(ValueError):
        ac.AcousticLink(directivity_index_db=_math.nan)


def test_max_range_rejects_degenerate_bracket():
    """The bisection bracket must satisfy 0 < lo < hi — not silently mis-answered."""
    link = ac.AcousticLink()
    with pytest.raises(ValueError):
        ac.max_link_range(link, lo=100.0, hi=10.0)
    with pytest.raises(ValueError):
        ac.max_link_range(link, lo=0.0, hi=10.0)
    with pytest.raises(ValueError):
        ac.max_link_range(link, lo=10.0, hi=10.0)
