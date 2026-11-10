"""Senaryo hesabı: bir deprem + nokta listesi → model bazında MMI medyanı ve sigması."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import gmice, gmpe, ipe
from .rupture import Rupture, build_rupture
from .site import assign_vs30

MODEL_LABELS = {
    "legacy": "Eski formül (doğrulanmamış)",
    "allen2012_rhyp": "Allen 2012 · Rhyp",
    "allen2012_rrup": "Allen 2012 · Rrup",
    "bayrak2019": "Bayrak 2019 · R3",
    "kale2015_wgrw12": "Kale 2015 → WGRW12",
    "kale2015_ba14": "Kale 2015 → Bilal & Askan 2014",
}


@dataclass
class Event:
    mag: float
    lat: float
    lon: float
    depth: float
    rake: float | None = None
    event_id: str = "senaryo"


def site_distances(rup: Rupture, lat, lon) -> pd.DataFrame:
    d = rup.distances(lat, lon)
    return pd.DataFrame(dict(lat=np.atleast_1d(lat), lon=np.atleast_1d(lon), **d))


def predict_models(mag: float, depth: float, rake: float, dist: pd.DataFrame, vs30,
                   models=tuple(MODEL_LABELS)) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Her model için (medyan MMI, σ_MMI) döndürür. ``dist`` repi/rhyp/rjb/rrup sütunlarını içermeli."""
    out = {}
    repi, rhyp, rjb, rrup = (dist[c].to_numpy(float) for c in ("repi", "rhyp", "rjb", "rrup"))
    if "legacy" in models:
        out["legacy"] = ipe.legacy_unverified(mag, repi, depth)
    if "allen2012_rhyp" in models:
        out["allen2012_rhyp"] = ipe.allen2012_rhyp(mag, rhyp)
    if "allen2012_rrup" in models:
        out["allen2012_rrup"] = ipe.allen2012_rrup(mag, rrup)
    if "bayrak2019" in models:
        out["bayrak2019"] = ipe.bayrak2019(mag, repi, depth, "R3")
    chain = [m for m in models if m.startswith("kale2015_")]
    if chain:
        ln_pgv, sd_ln = gmpe.kale2015_pgv(mag, rake, rjb, vs30)
        pgv = np.exp(ln_pgv)
        for m in chain:
            mmi, slope, sd_g = gmice.GMICES[m.split("_", 1)[1]](pgv)
            out[m] = (mmi, gmice.chain_sigma(slope, sd_ln, sd_g))
    return out


def run_scenario(event: Event, lat, lon, vs30=None, rupture: Rupture | None = None, models=tuple(MODEL_LABELS),
                 vs30_raster=None, rupture_geojson=None):
    """Tam senaryo: kaynak geometrisi, Vs30, uzaklıklar ve tüm model tahminleri.

    Dönüş: (DataFrame, Rupture). DataFrame'de her model için ``<model>`` (medyan) ve ``<model>_sd`` sütunları bulunur.
    """
    rake = 0.0 if event.rake is None else event.rake
    rup = rupture or build_rupture(event.mag, event.lat, event.lon, event.depth, rake=event.rake,
                                   rupture_geojson=rupture_geojson)
    if rup.is_finite and event.rake is None:
        rake = rup.rake
    df = site_distances(rup, lat, lon)
    kw = {} if vs30_raster is None else {"raster": vs30_raster}
    v, vsrc = assign_vs30(df.lat.to_numpy(), df.lon.to_numpy(), given=vs30, **kw)
    df["vs30"] = v
    for k, (mu, sd) in predict_models(event.mag, event.depth, rake, df, v, models).items():
        df[k] = mu
        df[f"{k}_sd"] = sd
    df.attrs.update(vs30_source=vsrc, rupture_source=rup.source, rake=rake)
    return df, rup
