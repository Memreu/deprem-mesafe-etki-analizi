"""Düzenli ızgara üzerinde senaryo hesabı (harita katmanları için)."""

from __future__ import annotations

import numpy as np

from .model import Event, run_scenario
from .rupture import LocalProjection
from .uncertainty import LogicTree, add_uncertainty


def make_grid(event: Event, half_width_km: float = 250.0, spacing_km: float = 10.0):
    proj = LocalProjection(event.lat, event.lon)
    v = np.arange(-half_width_km, half_width_km + 1e-9, spacing_km)
    X, Y = np.meshgrid(v, v)
    lon, lat = proj.lonlat(X.ravel(), Y.ravel())
    return np.asarray(lat), np.asarray(lon), X.shape


def run_grid(event: Event, half_width_km=250.0, spacing_km=10.0, vs30=None, tree: LogicTree | None = None,
             rupture=None, rupture_geojson=None):
    lat, lon, shape = make_grid(event, half_width_km, spacing_km)
    df, rup = run_scenario(event, lat, lon, vs30=vs30, rupture=rupture, rupture_geojson=rupture_geojson)
    df = add_uncertainty(df, tree, finite=rup.is_finite)
    df.attrs["grid_shape"] = shape
    return df, rup
