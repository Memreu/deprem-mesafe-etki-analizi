"""Aşama 1 testleri: OpenQuake ile birebir eşleşme ve geometri doğrulaması."""

import numpy as np
import pytest

oq = pytest.importorskip("openquake.hazardlib")

from openquake.hazardlib.contexts import RuptureContext, get_mean_stds  # noqa: E402
from openquake.hazardlib.geo import Mesh, Point  # noqa: E402
from openquake.hazardlib.geo.surface import PlanarSurface  # noqa: E402
from openquake.hazardlib.gsim.allen_2012_ipe import AllenEtAl2012, AllenEtAl2012Rhypo  # noqa: E402
from openquake.hazardlib.imt import MMI  # noqa: E402

from mmi_mapper import gmice, ipe, rupture  # noqa: E402
from mmi_mapper.model import Event, run_scenario  # noqa: E402

R = np.array([1.0, 5, 20, 49, 51, 100, 250, 400])


@pytest.mark.parametrize("mag", [5.0, 6.3, 7.8])
def test_allen2012_matches_openquake(mag):
    ctx = RuptureContext()
    ctx.mag = mag
    ctx.rrup = R
    ctx.rhypo = R
    ctx.sids = np.arange(len(R))
    for ours, cls in ((ipe.allen2012_rrup, AllenEtAl2012), (ipe.allen2012_rhyp, AllenEtAl2012Rhypo)):
        mean, sd = ours(mag, R)
        oq_mean, oq_sd, _, _ = get_mean_stds(cls(), ctx, [MMI()])
        np.testing.assert_allclose(mean, oq_mean[0], atol=1e-10)
        np.testing.assert_allclose(sd, oq_sd[0], atol=1e-10)


def test_wgrw12_continuity_and_known_values():
    # Parçalı doğrunun kırılma noktalarında süreklilik (ShakeMap uygulaması ile aynı katsayılar)
    for lp in (-1.21, 0.53):
        lo, _, _ = gmice.wgrw12_pgv(10 ** (lp - 1e-9))
        hi, _, _ = gmice.wgrw12_pgv(10 ** (lp + 1e-9))
        assert abs(lo - hi) < 0.02
    mmi, _, sd = gmice.wgrw12_pgv(np.array([10.0]))
    assert mmi[0] == pytest.approx(2.89 + 3.16 * 1.0)
    assert sd[0] == 0.63


def test_bilal_askan_abstract_equation():
    mmi, slope, _ = gmice.bilal_askan2014_pgv(np.array([30.0]))
    assert mmi[0] == pytest.approx(2.673 + 4.340 * np.log10(30.0))
    assert slope[0] == pytest.approx(4.340 * np.log10(np.e))


def test_finite_fault_distances_match_openquake_planar_surface():
    r = rupture.rupture_from_trace(7.0, 37.0, 37.0, 10.0, [(36.8, 36.9), (37.2, 37.1)], dip=45, ztor=2, width=20)
    q = r.quads[0]
    lo, la = r.proj.lonlat(q[:, 0], q[:, 1])
    surf = PlanarSurface.from_corner_points(*[Point(lo[i], la[i], q[i, 2]) for i in range(4)])
    rng = np.random.default_rng(0)
    lat, lon = 36.5 + rng.random(150), 36.5 + rng.random(150)
    mesh = Mesh(lon, lat, np.zeros_like(lon))
    d = r.distances(lat, lon)
    np.testing.assert_allclose(d["rrup"], surf.get_min_distance(mesh), atol=0.3)
    np.testing.assert_allclose(d["rjb"], surf.get_joyner_boore_distance(mesh), atol=0.3)


def test_vertical_fault_rrup_shapely():
    r = rupture.rupture_from_trace(7.0, 37.0, 37.0, 10.0, [(36.8, 37.0), (37.2, 37.0)], dip=90, ztor=0, width=15)
    d = r.distances([37.0, 37.2], [37.0, 37.0])
    assert d["rjb"][0] < 0.05 and d["rrup"][0] < 0.05
    assert d["rjb"][1] == pytest.approx(d["rrup"][1], abs=0.05)


def test_thingbaijam_strike_slip_length():
    L, W = rupture.thingbaijam2017(7.8, 0.0)
    assert L == pytest.approx(10 ** (-2.943 + 0.681 * 7.8))
    assert W == pytest.approx(10 ** (-0.543 + 0.261 * 7.8))


def test_kahramanmaras_gem_rupture_is_finite_and_closer():
    ev = Event(mag=7.8, lat=37.226, lon=37.014, depth=10.0)
    df, rup = run_scenario(ev, [36.2023], [36.1613], vs30=400)  # Antakya
    assert rup.is_finite and rup.length > 200
    assert df.rjb.iloc[0] < df.repi.iloc[0] / 3
    # sonlu fayla Allen Rrup, nokta kaynak Rhyp'ten belirgin yüksek olmalı
    assert df.allen2012_rrup.iloc[0] > df.allen2012_rhyp.iloc[0] + 1.0
