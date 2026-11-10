import numpy as np
import pytest

from mmi_mapper import ipe
from mmi_mapper.coords import dms_to_decimal, haversine_km


def test_dms():
    assert dms_to_decimal("39°55'29.1\"N") == pytest.approx(39.92475, abs=1e-5)
    assert dms_to_decimal("32°50'12.6\"W") < 0


def test_haversine_one_degree_lat():
    assert haversine_km(37, 37, 38, 37) == pytest.approx(111.2, abs=0.2)


def test_legacy_overpredicts_vs_allen_at_100_300_km():
    # Literatür taramasındaki iddia: eski formül 100–300 km'de ~1,5–2 MMI fazla tahmin eder
    for mw in (6.0, 7.0, 7.8):
        r = np.array([100.0, 200.0, 300.0])
        old, _ = ipe.legacy_unverified(mw, r, 10.0)
        allen, _ = ipe.allen2012_rhyp(mw, np.hypot(r, 10.0))
        diff = old - allen
        assert np.all(diff > 1.4) and np.all(diff < 2.3)


def test_bayrak_monotonic_and_sigma():
    r = np.array([5, 20, 50, 100, 200.0])
    for m in ipe.BAYRAK2019:
        mean, sd = ipe.bayrak2019(7.0, r, 10.0, m)
        assert np.all(np.diff(mean) < 0)
        assert np.allclose(sd, ipe.BAYRAK2019[m]["sigma"])


def test_allen_sigma_limits():
    _, sd = ipe.allen2012_rrup(7.0, np.array([0.0, 1e4]))
    assert sd[0] == pytest.approx(0.95)
    assert sd[1] == pytest.approx(0.72, abs=1e-3)
