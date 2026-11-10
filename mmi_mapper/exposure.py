"""Nüfus maruziyeti (USGS PAGER mantığı): şiddet düzeyine göre etkilenen nüfus.

PAGER, nüfusu tahmin edilen MMI sınıflarına (I, II–III, IV, … X+) göre toplar
(Jaiswal & Wald 2010). Burada iki nüfus kaynağı desteklenir:

1. **Nokta nüfus (varsayılan, çevrimdışı):** GeoNames ``cities15000`` kümesi (nüfusu ≥ 15 000 olan yerleşimler),
   ``geonamescache`` paketiyle birlikte gelir. Lisans: CC BY 4.0 (GeoNames). Kırsal nüfusu içermediği için
   PAGER/GHSL değerlerinden **düşüktür**; göreli karşılaştırma içindir.
2. **Nüfus rasteri:** GHSL GHS-POP ya da TÜİK tabanlı bir GeoTIFF (``raster=...``), rasterio ile okunur.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PAGER_BINS = [("I", -np.inf, 1.5), ("II–III", 1.5, 3.5), ("IV", 3.5, 4.5), ("V", 4.5, 5.5), ("VI", 5.5, 6.5),
              ("VII", 6.5, 7.5), ("VIII", 7.5, 8.5), ("IX", 8.5, 9.5), ("X+", 9.5, np.inf)]


def geonames_points(lat_range, lon_range, min_population=15000) -> pd.DataFrame:
    import geonamescache

    cities = geonamescache.GeonamesCache(min_city_population=15000).get_cities().values()
    df = pd.DataFrame([{k: c[k] for k in ("name", "latitude", "longitude", "population", "countrycode")}
                       for c in cities])
    df = df.rename(columns={"latitude": "lat", "longitude": "lon"})
    sel = df.lat.between(*lat_range) & df.lon.between(*lon_range) & (df.population >= min_population)
    return df[sel].reset_index(drop=True)


def raster_points(path, lat_range, lon_range) -> pd.DataFrame:
    """Nüfus rasterindeki (EPSG:4326) hücre merkezlerini nokta olarak döndürür."""
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(path) as src:
        win = from_bounds(lon_range[0], lat_range[0], lon_range[1], lat_range[1], src.transform)
        arr = src.read(1, window=win).astype(float)
        tr = src.window_transform(win)
        if src.nodata is not None:
            arr[arr == src.nodata] = 0
    rows, cols = np.nonzero(arr > 0)
    xs, ys = rasterio.transform.xy(tr, rows, cols)
    return pd.DataFrame(dict(name="", lat=np.asarray(ys), lon=np.asarray(xs), population=arr[rows, cols],
                             countrycode=""))


def pager_table(mmi_columns: dict[str, np.ndarray], population: np.ndarray) -> pd.DataFrame:
    """Her senaryo (ör. %16/%50/%84) için MMI sınıfına göre toplam nüfus."""
    out = {"MMI": [b[0] for b in PAGER_BINS]}
    for name, mmi in mmi_columns.items():
        mmi = np.asarray(mmi, float)
        out[name] = [float(population[(mmi >= lo) & (mmi < hi)].sum()) for _, lo, hi in PAGER_BINS]
    return pd.DataFrame(out)


def exposure(event, half_width_deg=3.0, raster=None, tree=None, vs30=None, rupture=None):
    """Senaryo için nüfus maruziyeti. (PAGER tablosu, yerleşim bazlı tablo) döndürür."""
    from .model import run_scenario
    from .uncertainty import add_uncertainty

    lat_r = (event.lat - half_width_deg, event.lat + half_width_deg)
    lon_r = (event.lon - half_width_deg * 1.3, event.lon + half_width_deg * 1.3)
    pts = raster_points(raster, lat_r, lon_r) if raster else geonames_points(lat_r, lon_r)
    df, rup = run_scenario(event, pts.lat.to_numpy(), pts.lon.to_numpy(), vs30=vs30, rupture=rupture)
    df = add_uncertainty(df, tree, finite=rup.is_finite)
    places = pd.concat([pts.reset_index(drop=True),
                        df[["rrup", "vs30", "lt_p16", "lt_p50", "lt_p84", "p_ge_7", "p_ge_8"]]], axis=1)
    table = pager_table({"%16": df.lt_p16, "Medyan": df.lt_p50, "%84": df.lt_p84}, pts.population.to_numpy(float))
    return table, places.sort_values("lt_p50", ascending=False).reset_index(drop=True), rup
