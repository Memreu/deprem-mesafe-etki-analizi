"""Benchmark depremleri: olay tablosu, fay geometrisi ve gözlemler.

Benchmark betiği, Streamlit arayüzü ve not defteri aynı seçimleri bu modülden alır:

* ``data/events.csv``: altı büyük depremin USGS ComCat parametreleri ve seçilen fay
  (ShakeMap → FFM → otomatik GEM).
* ``data/observations/usgs_observations.csv``: DYFI, ShakeMap istasyonları (AFAD, KOERI vd.)
  ve makrosismik saha şiddetleri.
* ``data/raw/<event_id>/afad_stations.csv`` ve ``field_map.csv`` varsa gözlemlere eklenir.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import observations as O
from .model import Event
from .rupture import Rupture, build_rupture

ROOT = Path(__file__).resolve().parent.parent
EVENTS_CSV = ROOT / "data" / "events.csv"
USGS_OBS = ROOT / "data" / "observations" / "usgs_observations.csv"
RAW = ROOT / "data" / "raw"

GEOMETRIES = {
    "auto": "USGS fayı (ShakeMap / FFM), yoksa otomatik GEM",
    "gem": "Otomatik GEM izi + Thingbaijam 2017",
    "point": "Nokta kaynak",
}


def load_events(path=EVENTS_CSV) -> pd.DataFrame:
    """Olay tablosu, ``event_id`` dizinli."""
    return pd.read_csv(path).set_index("event_id")


def get_event(event_id: str, events: pd.DataFrame | None = None) -> Event:
    e = (load_events() if events is None else events).loc[event_id]
    return Event(mag=float(e.mag), lat=float(e.lat), lon=float(e.lon), depth=float(e.depth_km), event_id=event_id)


def rupture_file(event_id: str, events: pd.DataFrame | None = None) -> Path | None:
    """Olay için repodaki USGS fay dosyası (yoksa ``None``)."""
    e = (load_events() if events is None else events).loc[event_id]
    f = e.get("rupture_file")
    return ROOT / f if isinstance(f, str) and f else None


def event_rupture(event_id: str, geometry: str = "auto", events: pd.DataFrame | None = None) -> Rupture:
    """``geometry``: 'auto' (data/events.csv'deki seçim), 'gem' (GEM + Thingbaijam) ya da 'point'."""
    if geometry not in GEOMETRIES:
        raise ValueError(f"Bilinmeyen geometri: {geometry!r} (seçenekler: {', '.join(GEOMETRIES)})")
    evs = load_events() if events is None else events
    ev = get_event(event_id, evs)
    if geometry == "point":
        return build_rupture(ev.mag, ev.lat, ev.lon, ev.depth, use_finite=False)
    f = rupture_file(event_id, evs)
    if geometry == "gem" or f is None:
        return build_rupture(ev.mag, ev.lat, ev.lon, ev.depth)
    return build_rupture(ev.mag, ev.lat, ev.lon, ev.depth, rupture_geojson=f)


def usgs_observations(event_id: str, path=USGS_OBS, raw_dir=RAW) -> pd.DataFrame:
    """Olayın tüm gözlemleri: repodaki USGS tablosu + varsa elle eklenen AFAD ve saha dosyaları."""
    u = pd.read_csv(path)
    parts = [u[u.event_id == event_id].drop(columns=["event_id"])]
    folder = Path(raw_dir) / event_id
    if (folder / "afad_stations.csv").exists():
        parts.append(O.load_afad_csv(folder / "afad_stations.csv"))
    if (folder / "field_map.csv").exists():
        parts.append(O.load_field_map(folder / "field_map.csv"))
    return pd.concat(parts, ignore_index=True)
