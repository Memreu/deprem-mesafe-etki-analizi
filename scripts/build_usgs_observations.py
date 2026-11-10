"""USGS indirmelerinden (data/raw/<event_id>/) benchmark için sıkıştırılmış olay, gözlem ve fay dosyaları üretir.

    python scripts/download_data.py usgs <event_id>     # her olay için
    python scripts/build_usgs_observations.py           # varsayılan: aşağıdaki EVENTS

Çıktılar
--------
* data/events.csv — olay parametreleri (ComCat tercih edilen çözüm) ve seçilen fay geometrisi.
* data/observations/usgs_observations.csv
    - USGS DYFI (cdi_geo.txt; ≥ 3 yanıt, şüpheli değil)
    - ShakeMap istasyon listesindeki sismik istasyonların PGV'si (aykırı işaretliler hariç; büyük yatay bileşen).
      Ağ kodu TK → "AFAD (ShakeMap)", KO → "KOERI (ShakeMap)", diğerleri → "istasyon (ShakeMap)".
    - ShakeMap istasyon listesindeki makrosismik saha şiddetleri (ağ kodu INTENSITY; ör. 1999 depremlerinin
      gözlenen şiddetleri, Sisam 2020 için EMSC) → "makrosismik (ShakeMap)".
  Vs30 tüm noktalarda USGS Global Vs30 rasterinden alınır (önce Türkiye kırpımı, sonra küresel ızgara; yoksa
  ShakeMap değeri). ShakeMap listesindeki değer ``vs30_shakemap`` sütununda saklanır.
* data/ruptures/<event_id>_<tür>.geojson — benchmark'ta kullanılan USGS fayı (bkz. ``choose_rupture``).

USGS verileri kamu malıdır.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mmi_mapper import observations as O  # noqa: E402
from mmi_mapper.rupture import rupture_from_gem, rupture_from_geojson, thingbaijam2017  # noqa: E402
from mmi_mapper.site import RASTER_CANDIDATES, sample_vs30_raster  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "observations" / "usgs_observations.csv"
EVENTS_CSV = ROOT / "data" / "events.csv"
RUP = ROOT / "data" / "ruptures"

EVENTS = {
    "us6000jllz": "Kahramanmaraş (Pazarcık) 2023",
    "us6000jlqa": "Kahramanmaraş (Elbistan) 2023",
    "us60007ewc": "Elazığ (Sivrice) 2020",
    "us7000c7y0": "Sisam / İzmir 2020",
    "usp0009hev": "Düzce 1999",
    "usp0009d4z": "Kocaeli (İzmit) 1999",
}
COLS = ["event_id", "source", "obs_type", "station", "network", "lat", "lon", "pgv_cms", "obs_mmi", "obs_mmi_ba14",
        "n_resp", "vs30", "vs30_source", "vs30_shakemap"]
NET_LABEL = {"TK": "AFAD (ShakeMap)", "KO": "KOERI (ShakeMap)"}
MIN_LENGTH_RATIO = 0.5


def event_params(eid: str) -> dict:
    d = json.loads((RAW / eid / "detail.json").read_text())
    lon, lat, depth = d["geometry"]["coordinates"]
    p = d["properties"]
    return dict(event_id=eid, name=EVENTS.get(eid, p.get("place")), mag=p["mag"], mag_type=p.get("magType"),
                lat=lat, lon=lon, depth_km=depth, time_ms=p.get("time"))


def choose_rupture(ev: dict) -> tuple[Path | None, str, float]:
    """Fay seçimi: ShakeMap rupture.json → USGS FFM → GEM otomatik.

    Bir USGS dosyası, uzunluğu Thingbaijam vd. (2017) medyan uzunluğunun en az yarısıysa kabul edilir.
    (Gerekçe: bazı eski ShakeMap Atlas olaylarının rupture.json dosyası yalnızca 5–20 km'lik tek bir parça içerir;
    ör. Mw 7.6 İzmit için 15 km. Bu, büyük bir depremi neredeyse nokta kaynağa indirger.)
    """
    gem = rupture_from_gem(ev["mag"], ev["lat"], ev["lon"], ev["depth_km"])
    l_ref = thingbaijam2017(ev["mag"], gem.rake if gem.is_finite else 0.0)[0]
    for name, kind in (("shakemap_rupture.json", "shakemap"), ("finite-fault_FFM.geojson", "ffm")):
        path = RAW / ev["event_id"] / name
        if path.exists():
            r = rupture_from_geojson(ev["mag"], ev["lat"], ev["lon"], ev["depth_km"], path)
            if r.is_finite and r.length >= MIN_LENGTH_RATIO * l_ref:
                return path, kind, r.length
    return None, "gem", gem.length


def macroseismic_points(stationlist: Path) -> pd.DataFrame:
    gj = json.loads(stationlist.read_text())
    rows = []
    for f in gj.get("features", []):
        p = f["properties"]
        if p.get("network") != "INTENSITY" or not isinstance(p.get("intensity"), (int, float)):
            continue
        if str(p.get("intensity_flag", "0")) not in ("0", ""):
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        rows.append(dict(station=p.get("code"), network="INTENSITY", lat=lat, lon=lon, obs_mmi=float(p["intensity"]),
                         vs30=p.get("vs30") if isinstance(p.get("vs30"), (int, float)) else np.nan))
    df = pd.DataFrame(rows)
    if len(df):
        df["obs_type"], df["source"] = "makrosismik", "makrosismik (ShakeMap)"
    return df


def raster_vs30(lat, lon) -> np.ndarray:
    r = np.full(len(lat), np.nan)
    for path in RASTER_CANDIDATES:  # önce Türkiye kırpımı, kalan noktalar için küresel ızgara (varsa)
        if path.exists() and np.isnan(r).any():
            miss = np.isnan(r)
            r[miss] = sample_vs30_raster(np.asarray(lat)[miss], np.asarray(lon)[miss], path)
    return r


def build(event_ids):
    parts, events = [], []
    RUP.mkdir(parents=True, exist_ok=True)
    for eid in event_ids:
        folder = RAW / eid
        ev = event_params(eid)
        path, kind, length = choose_rupture(ev)
        ev.update(rupture=kind, rupture_length_km=round(length, 1))
        if path is not None:
            target = RUP / f"{eid}_{kind}.geojson"
            shutil.copy(path, target)
            ev["rupture_file"] = str(target.relative_to(ROOT))
        events.append(ev)

        sl = folder / "shakemap_stationlist.json"
        obs = []
        dyfi = folder / "dyfi_cdi_geo.txt"
        if dyfi.exists():
            obs.append(O.load_dyfi(dyfi))
        if sl.exists():
            st = O.load_shakemap_stations(sl)
            if len(st):
                st["source"] = st["network"].map(NET_LABEL).fillna("istasyon (ShakeMap)")
                obs.append(st)
            ms = macroseismic_points(sl)
            if len(ms):
                obs.append(ms)
        for d in obs:
            d["event_id"] = eid
            d["vs30_shakemap"] = d["vs30"] if "vs30" in d else np.nan
            r = raster_vs30(d.lat.to_numpy(), d.lon.to_numpy())
            d["vs30"] = np.where(np.isfinite(r), r, d["vs30_shakemap"])
            d["vs30_source"] = np.where(np.isfinite(r), "USGS Vs30 rasteri", "ShakeMap")
            parts.append(d.reindex(columns=COLS))
    df = pd.concat(parts, ignore_index=True)
    df.to_csv(OUT, index=False, float_format="%.5g")
    pd.DataFrame(events).to_csv(EVENTS_CSV, index=False)
    print(pd.DataFrame(events)[["event_id", "name", "mag", "rupture", "rupture_length_km"]].to_string(index=False))
    print(df.groupby(["event_id", "source"]).size().to_string())


if __name__ == "__main__":
    build(sys.argv[1:] or list(EVENTS))
