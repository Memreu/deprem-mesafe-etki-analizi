"""Zemin koşulu (Vs30) ataması.

Öncelik sırası:
1. USGS Global Vs30 Mosaic rasteri. Repoda Türkiye ve çevresi için kırpılmış sürüm vardır
   (``data/vs30/vs30_turkey.tif``, 24–46°D, 33–43.5°K, 30 yay saniyesi). Küresel ızgara için:
   ``python scripts/download_data.py vs30`` → ``data/raw/global_vs30.grd``.
   Kaynak: Heath vd. (2020), USGS; topoğrafik eğim vekili Wald & Allen (2007) temellidir.
2. Kullanıcının verdiği istasyon/nokta Vs30 değerleri.
3. Sabit referans değer (varsayılan 760 m/s, NEHRP B/C sınırı) — uyarıyla.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent.parent / "data"
RASTER_CANDIDATES = [_DATA / "vs30" / "vs30_turkey.tif", _DATA / "raw" / "global_vs30.grd", _DATA / "raw" / "global_vs30.tif"]


def _default_raster():
    for p in RASTER_CANDIDATES:
        if p.exists():
            return p
    return RASTER_CANDIDATES[0]


DEFAULT_RASTER = _default_raster()
REFERENCE_VS30 = 760.0


def sample_vs30_raster(lat, lon, path: str | os.PathLike = DEFAULT_RASTER) -> np.ndarray:
    """Rasterdan en yakın hücre değerini örnekler (rasterio gerekir)."""
    import rasterio

    lat = np.atleast_1d(np.asarray(lat, float))
    lon = np.atleast_1d(np.asarray(lon, float))
    with rasterio.open(path) as src:
        vals = np.array([v[0] for v in src.sample(zip(lon, lat))], dtype=float)
        if src.nodata is not None:
            vals[vals == src.nodata] = np.nan
    vals[(vals <= 0) | ~np.isfinite(vals)] = np.nan
    return vals


def assign_vs30(lat, lon, raster: str | os.PathLike | None = DEFAULT_RASTER, fallback: float = REFERENCE_VS30,
                given=None) -> tuple[np.ndarray, str]:
    """Her noktaya Vs30 atar. (vs30, kaynak etiketi) döndürür."""
    n = np.atleast_1d(lat).size
    if given is not None:
        v = np.broadcast_to(np.asarray(given, float), (n,)).copy()
        return v, "kullanıcı"
    if raster is not None and Path(raster).exists():
        try:
            v = sample_vs30_raster(lat, lon, raster)
            v = np.where(np.isnan(v), fallback, v)
            return v, "USGS Vs30 rasteri"
        except ImportError:
            warnings.warn("rasterio kurulu değil; sabit Vs30 kullanılıyor.", stacklevel=2)
    warnings.warn(f"Vs30 rasteri bulunamadı ({raster}); tüm noktalara {fallback} m/s atandı.", stacklevel=2)
    return np.full(n, float(fallback)), f"sabit {fallback:.0f} m/s"


def nehrp_class(vs30) -> np.ndarray:
    """NEHRP zemin sınıfı (A–E) — BSSC sınırları: 1500, 760, 360, 180 m/s."""
    v = np.asarray(vs30, float)
    return np.select([v > 1500, v > 760, v > 360, v > 180], ["A", "B", "C", "D"], "E")
