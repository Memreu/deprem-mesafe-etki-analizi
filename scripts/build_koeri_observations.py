"""KOERI kuvvetli yer hareketi özellik tablosundan gözlem dosyası üretir.

Kaynak: Ayberkrk/turkiye-deprem-verisi, data/processed/event_station_table.csv
(commit ed2305c39e8265b272e73f241f291bdfac7d50aa). Kayıtlar KOERI / ORFEUS-EIDA'dan,
Vs30 USGS Global Vs30 Mosaic'ten gelir.

Kullanım:  python scripts/build_koeri_observations.py <event_station_table.csv>
"""

import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "observations" / "koeri_strong_motion.csv"

COLS = {
    "event_id": "event_id", "window_group": "window_group", "time_utc": "time_utc",
    "event_latitude": "ev_lat", "event_longitude": "ev_lon", "depth_km": "ev_depth_km", "mw_estimate": "mw",
    "station": "station", "network": "network", "station_latitude": "sta_lat", "station_longitude": "sta_lon",
    "vs30_ms": "vs30", "nehrp_site_class": "nehrp", "pgv_geomean_cms": "pgv_cms", "pga_geomean_g": "pga_g",
    "snr_db": "snr_db",
}


def main(src):
    d = pd.read_csv(src)
    keep = (d.usable_for_engineering == True) & d.mw_estimate.notna() & (d.pgv_geomean_cms > 0)  # noqa: E712
    keep &= d.label_ambiguous != True  # noqa: E712  (pencerede daha büyük başka deprem olan kayıtlar)
    out = d.loc[keep, list(COLS)].rename(columns=COLS)
    out["window_group"] = out["window_group"].fillna(out["event_id"])
    out.sort_values(["time_utc", "station"]).to_csv(OUT, index=False, float_format="%.6g")
    print(f"{len(out)} kayıt, {out.event_id.nunique()} deprem, {out.station.nunique()} istasyon -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
