"""Gözlem yükleyicileri. Hepsi ortak bir tablo döndürür:

    lat, lon, obs_mmi, obs_type, source  (+ varsa pgv_cms, vs30, station, n_resp)

* Enstrümantal (PGV → MMI): KOERI tablosu, ShakeMap stationlist.json, AFAD CSV.
  ``obs_mmi`` varsayılan olarak Worden vd. (2012) ile hesaplanır (ShakeMap uygulaması);
  ``obs_mmi_ba14`` sütunu Bilal & Askan (2014) karşılığını da tutar.
* Makrosismik: USGS DYFI (cdi_geo / cdi_zip), saha haritası CSV'si (lat, lon, mmi).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .gmice import bilal_askan2014_pgv, wgrw12_pgv

DATA = Path(__file__).resolve().parent.parent / "data"
KOERI = DATA / "observations" / "koeri_strong_motion.csv"


def _instrumental(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["obs_mmi"] = wgrw12_pgv(df["pgv_cms"].to_numpy(float))[0]
    df["obs_mmi_ba14"] = bilal_askan2014_pgv(df["pgv_cms"].to_numpy(float))[0]
    df["obs_type"] = "enstrümantal"
    return df


def load_koeri(path=KOERI, event_id: str | None = None, min_mw: float | None = None) -> pd.DataFrame:
    """KOERI kuvvetli yer hareketi kayıtları (bkz. data/observations/README.md)."""
    d = pd.read_csv(path)
    if event_id is not None:
        d = d[d.event_id == event_id]
    if min_mw is not None:
        d = d[d.mw >= min_mw]
    d = d.rename(columns={"sta_lat": "lat", "sta_lon": "lon"})
    d["source"] = "KOERI"
    return _instrumental(d)


def _find(cols, *patterns):
    for p in patterns:
        for c in cols:
            if re.fullmatch(p, c.strip(), flags=re.IGNORECASE):
                return c
    return None


def load_dyfi(path, min_responses: int = 3) -> pd.DataFrame:
    """USGS DYFI geokodlu/ilçe tablosu (cdi_geo.txt, cdi_geo_1km.txt, cdi_zip.txt).

    Biçim: ``# Columns: Geocoded box,CDI,No. of responses,Hypocentral distance,Latitude,Longitude,Suspect?,...``
    başlık satırı ve tırnaklı CSV satırları. Şüpheli (Suspect? = 1) hücreler atılır; en az ``min_responses``
    yanıtlı hücreler tutulur.
    """
    import csv

    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    header = None
    rows = []
    for line in lines:
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            body = body.split(":", 1)[1] if body.lower().startswith("columns:") else body
            cand = [c.strip().rstrip("[").strip() for c in body.replace("[,", ",").replace("]", "").split(",")]
            if any(re.fullmatch("cdi|mmi", c, re.I) for c in cand):
                header = cand
            continue
        if line.strip():
            rows.append(next(csv.reader([line])))
    if header is None:
        df = pd.read_csv(path)
    else:
        n = len(header)
        df = pd.DataFrame([r[:n] + [""] * (n - len(r)) for r in rows], columns=header)
    cols = list(df.columns)
    c_cdi = _find(cols, r"cdi", r"mmi", r"intensity")
    c_lat = _find(cols, r"lat(itude)?")
    c_lon = _find(cols, r"lon(gitude)?")
    c_n = _find(cols, r"(no\.? of )?responses?", r"nresp", r"n_resp", r"numresp")
    c_sus = _find(cols, r"suspect\??")
    c_dist = _find(cols, r"hypocentral distance")
    if None in (c_cdi, c_lat, c_lon):
        raise ValueError(f"DYFI dosyasında CDI/enlem/boylam sütunları bulunamadı: {cols}")
    out = pd.DataFrame({"lat": pd.to_numeric(df[c_lat], errors="coerce"),
                        "lon": pd.to_numeric(df[c_lon], errors="coerce"),
                        "obs_mmi": pd.to_numeric(df[c_cdi], errors="coerce")})
    if c_dist is not None:
        out["dyfi_rhyp_km"] = pd.to_numeric(df[c_dist], errors="coerce")
    if c_sus is not None:
        out = out[pd.to_numeric(df[c_sus], errors="coerce").fillna(0).to_numpy() == 0]
    if c_n is not None:
        out["n_resp"] = pd.to_numeric(df.loc[out.index, c_n], errors="coerce")
        out = out[out.n_resp >= min_responses]
    out = out.dropna(subset=["lat", "lon", "obs_mmi"])
    out["obs_type"], out["source"] = "DYFI", "USGS DYFI"
    return out.reset_index(drop=True)


def load_shakemap_stations(path, networks: tuple[str, ...] | None = None) -> pd.DataFrame:
    """ShakeMap stationlist.json içindeki sismik istasyonların PGV değerleri (cm/s).

    PGV, özellikteki ``pgv`` alanından ya da kanal genliklerinin (``channels[].amplitudes[]``,
    name == 'pgv') en büyüğünden okunur. ``networks`` verilirse yalnızca o ağlar tutulur
    (ör. AFAD için ('TK',)).
    """
    gj = json.loads(Path(path).read_text())
    rows = []
    for f in gj.get("features", []):
        p = f.get("properties", {})
        # ShakeMap istasyon listesi DYFI hücrelerini de "macroseismic" olarak içerir; yalnızca sismik istasyonlar
        if str(p.get("station_type", "seismic")).lower() != "seismic":
            continue
        flags = [str(a.get("flag", "0")) for ch in p.get("channels", []) for a in ch.get("amplitudes", [])
                 if str(a.get("name", "")).lower() == "pgv" and not str(ch.get("name", "")).upper().endswith("Z")]
        if flags and all(f != "0" for f in flags):
            continue  # ShakeMap'in aykırı (Outlier) olarak işaretlediği istasyonlar
        net = str(p.get("network", p.get("source", "")))
        if networks and net not in networks:
            continue
        pgv = p.get("pgv")
        if not isinstance(pgv, (int, float)):
            vals = [a.get("value") for ch in p.get("channels", []) for a in ch.get("amplitudes", [])
                    if str(a.get("name", "")).lower() == "pgv" and isinstance(a.get("value"), (int, float))
                    and str(a.get("flag", "0")) == "0" and not str(ch.get("name", "")).upper().endswith("Z")]
            pgv = max(vals) if vals else None
        if pgv is None or pgv <= 0:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        vs30 = p.get("vs30")
        rows.append(dict(station=p.get("code", p.get("id")), network=net, lat=lat, lon=lon, pgv_cms=float(pgv),
                         vs30=float(vs30) if isinstance(vs30, (int, float)) else np.nan))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["source"] = "ShakeMap istasyon"
    return _instrumental(df)


def load_afad_csv(path) -> pd.DataFrame:
    """Elle indirilen AFAD TADAS istasyon tablosu: station, lat, lon, pgv_cms [, vs30]."""
    df = pd.read_csv(path)
    missing = {"lat", "lon", "pgv_cms"} - set(df.columns)
    if missing:
        raise ValueError(f"AFAD tablosunda eksik sütunlar: {missing}")
    df["source"] = "AFAD"
    return _instrumental(df)


def load_field_map(path, scale: str = "MMI") -> pd.DataFrame:
    """Saha araştırması şiddet noktaları (ör. Albayrak vd. 2024 sayısallaştırması): lat, lon, mmi."""
    df = pd.read_csv(path)
    c = _find(list(df.columns), r"mmi", r"intensity", r"ems98?", r"i")
    out = pd.DataFrame({"lat": df["lat"], "lon": df["lon"], "obs_mmi": pd.to_numeric(df[c], errors="coerce")})
    out["obs_type"], out["source"] = "saha", f"saha haritası ({scale})"
    return out.dropna()


def vs30_from_stationlist(df: pd.DataFrame, path, max_km: float = 7.0) -> pd.DataFrame:
    """Vs30'u eksik noktalara, ShakeMap stationlist.json'daki en yakın noktanın Vs30 değerini atar.

    ShakeMap, istasyon listesindeki her noktaya (sismik istasyon ve DYFI hücresi) USGS Global Vs30 ızgarasından
    değer atar. USGS rasteri indirilemediğinde bu değerler ``max_km`` içindeki en yakın komşu ile kullanılır.
    """
    from .coords import haversine_km

    gj = json.loads(Path(path).read_text())
    pts = np.array([(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], f["properties"]["vs30"])
                    for f in gj.get("features", []) if isinstance(f["properties"].get("vs30"), (int, float))])
    df = df.copy()
    if "vs30" not in df:
        df["vs30"] = np.nan
    df["vs30_source"] = np.where(df["vs30"].notna(), "gözlem", "")
    if len(pts) == 0:
        return df
    for i in np.where(df["vs30"].isna())[0]:
        d = haversine_km(df.lat.iloc[i], df.lon.iloc[i], pts[:, 0], pts[:, 1])
        j = int(np.argmin(d))
        if d[j] <= max_km:
            df.iloc[i, df.columns.get_loc("vs30")] = pts[j, 2]
            df.iloc[i, df.columns.get_loc("vs30_source")] = "ShakeMap (en yakın komşu)"
    return df
