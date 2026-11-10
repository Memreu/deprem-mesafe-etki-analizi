"""USGS indirmelerinden (data/raw/<event_id>/) benchmark için sıkıştırılmış gözlem ve fay dosyaları üretir.

    python scripts/download_data.py usgs us6000jllz
    python scripts/build_usgs_observations.py us6000jllz us6000jlqa

Çıktılar:
* data/observations/usgs_observations.csv — DYFI (cdi_geo.txt, ≥3 yanıt, şüpheli değil) ve ShakeMap istasyon
  listesindeki AFAD (ağ kodu TK) istasyonlarının PGV'leri; Vs30 ShakeMap'in atadığı değerlerdir.
* data/ruptures/<event_id>_shakemap_rupture.json — ShakeMap'in kullandığı sonlu fay.
USGS verileri kamu malıdır.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mmi_mapper import observations as O  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "observations" / "usgs_observations.csv"
RUP = ROOT / "data" / "ruptures"
COLS = ["event_id", "source", "obs_type", "station", "network", "lat", "lon", "pgv_cms", "obs_mmi", "obs_mmi_ba14",
        "n_resp", "vs30", "vs30_source"]


def build(event_ids):
    parts = []
    RUP.mkdir(parents=True, exist_ok=True)
    for eid in event_ids:
        folder = RAW / eid
        sl = folder / "shakemap_stationlist.json"
        dy = O.vs30_from_stationlist(O.load_dyfi(folder / "dyfi_cdi_geo.txt"), sl)
        st = O.load_shakemap_stations(sl, networks=("TK",))
        st["source"], st["vs30_source"] = "AFAD (ShakeMap)", "ShakeMap"
        for d in (dy, st):
            d["event_id"] = eid
            parts.append(d.reindex(columns=COLS))
        if (folder / "shakemap_rupture.json").exists():
            shutil.copy(folder / "shakemap_rupture.json", RUP / f"{eid}_shakemap_rupture.json")
    df = pd.concat(parts, ignore_index=True)
    df.to_csv(OUT, index=False, float_format="%.5g")
    print(df.groupby(["event_id", "source"]).size())


if __name__ == "__main__":
    build(sys.argv[1:] or ["us6000jllz", "us6000jlqa"])
