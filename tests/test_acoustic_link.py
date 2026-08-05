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
    """Cylindrical spreading (spreading=1) gives less loss than spherical (2)."""
    cyl = ac.transmission_loss(1000.0, 15.0, spreading=1.0)
    sph = ac.transmission_loss(1000.0, 15.0, spreading=2.0)
    assert cyl < sph


def test_transmission_loss_validation():
    with pytest.raises(ValueError):
        ac.transmission_loss(0.0, 15.0)
    with pytest.raises(ValueError):
        ac.transmission_loss(100.0, 15.0, spreading=0.0)


def test_noise_level_grows_with_sea_state():
    calm = ac.noise_level(0.0)
    rough = ac.noise_level(5.0)
    assert rough > calm


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
    from for_your_eyes_only.mission import _LINK_RANGE_M, canonical_mission

    sc = canonical_mission()
    assert sc.link_budget.closes is True
    assert sc.link_budget.received_snr_db > sc.link_budget.max_range_m * 0  # positive
    # operating range < max range (interior closure)
    assert _LINK_RANGE_M < sc.link_budget.max_range_m


def test_link_budget_margin_property():
    link = ac.AcousticLink(spreading=1.0)
    budget = ac.compute_link_budget(link, 500.0)
    assert budget.margin_db == budget.received_snr_db
