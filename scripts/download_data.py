"""Doğrulama ve zemin verilerini indirir (USGS ComCat ürünleri, Vs30 rasteri).

Kullanım
--------
    python scripts/download_data.py usgs us6000jllz          # DYFI, ShakeMap istasyonları, rupture.json, FFM
    python scripts/download_data.py vs30                     # USGS Global Vs30 Mosaic (~610 MB)

USGS ürün dosya adları sürümden sürüme değişebildiği için, ComCat olay detayındaki
ürün içeriği (contents) son ekine göre aranır. Dosyalar ``data/raw/<event_id>/`` altına yazılır.

AFAD TADAS istasyon verisi otomatik indirilemez (oturum gerektirir). https://tadas.afad.gov.tr
adresinden indirilen istasyon tablosunu ``data/raw/<event_id>/afad_stations.csv`` olarak kaydedin;
beklenen sütunlar: station, lat, lon, pgv_cms (ve varsa vs30, rjb_km).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
VS30_URL = "https://apps.usgs.gov/shakemap_geodata/vs30/global_vs30.grd"  # https://earthquake.usgs.gov/data/vs30/
COMCAT = "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={eid}&format=geojson"
WANTED = {
    "dyfi": ["cdi_geo_1km.txt", "cdi_geo.txt", "cdi_zip.txt"],
    "shakemap": ["stationlist.json", "rupture.json"],
    "finite-fault": ["FFM.geojson"],
}


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 (sabit USGS alan adı)
        return r.read()


def download_usgs(event_id: str) -> list[Path]:
    detail = json.loads(_get(COMCAT.format(eid=event_id)))
    out_dir = RAW / event_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "detail.json").write_text(json.dumps(detail))
    saved = []
    products = detail["properties"].get("products", {})
    for ptype, suffixes in WANTED.items():
        if ptype not in products:
            print(f"  - {ptype}: ürün yok")
            continue
        contents = products[ptype][0]["contents"]
        for suf in suffixes:
            keys = [k for k in contents if k.endswith(suf)]
            if not keys:
                continue
            target = out_dir / f"{ptype}_{suf}"
            target.write_bytes(_get(contents[keys[0]]["url"]))
            saved.append(target)
            print(f"  ✓ {target.relative_to(RAW.parent.parent)}")
    return saved


def download_vs30(url: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / Path(url).name
    print(f"İndiriliyor: {url}")
    urllib.request.urlretrieve(url, target)  # noqa: S310
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("usgs")
    u.add_argument("event_id")
    v = sub.add_parser("vs30")
    v.add_argument("--url", default=VS30_URL,
                   help="USGS Global Vs30 Mosaic ızgarası (varsayılan: %(default)s, ~610 MB)")
    a = p.parse_args(argv)
    try:
        if a.cmd == "usgs":
            download_usgs(a.event_id)
        else:
            download_vs30(a.url)
    except OSError as e:
        sys.exit(f"İndirme başarısız: {e}")


if __name__ == "__main__":
    main()
