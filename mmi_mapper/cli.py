"""Etkileşimli komut satırı arayüzü (projenin orijinal kullanım biçimi)."""

from __future__ import annotations

import argparse
import webbrowser

import numpy as np

from . import ipe
from .coords import haversine_km, hypocentral_km, parse_coordinate
from .scale import describe, to_roman


def _ask_float(prompt: str) -> float:
    return float(input(prompt).replace(",", "."))


def point_source_table(mw: float, depth: float, eq_lat: float, eq_lon: float, sites: list[tuple[float, float]]):
    """Nokta kaynak IPE tahminleri (Aşama 0 modelleri)."""
    lat = np.array([s[0] for s in sites])
    lon = np.array([s[1] for s in sites])
    repi = haversine_km(eq_lat, eq_lon, lat, lon)
    rhyp = hypocentral_km(repi, depth)
    allen, allen_sd = ipe.allen2012_rhyp(mw, rhyp)
    bayrak, bayrak_sd = ipe.bayrak2019(mw, repi, depth, "R3")
    legacy, _ = ipe.legacy_unverified(mw, repi, depth)
    return dict(lat=lat, lon=lon, repi=repi, rhyp=rhyp, allen=allen, allen_sd=allen_sd,
                bayrak=bayrak, bayrak_sd=bayrak_sd, legacy=legacy)


def interactive() -> None:
    print("\n📘 Episantral uzaklık: yüzeyde episantra olan uzaklık.")
    print("📘 Hiposantral uzaklık: depremin yer altındaki odağına (hiposantr) olan uzaklık.\n")
    print("📍 Episantr koordinatları (ondalık 37.226 ya da DMS 37°13'33.6\"N):")
    eq_lat = parse_coordinate(input("Enlem: "))
    eq_lon = parse_coordinate(input("Boylam: "))
    sites = []
    print("\n👤 Konum(lar) — bitirmek için 'q'.")
    while True:
        s = input("Enlem (veya q): ")
        if s.strip().lower() == "q":
            break
        sites.append((parse_coordinate(s), parse_coordinate(input("Boylam: "))))
    if not sites:
        raise ValueError("En az bir konum girmelisiniz.")
    depth = _ask_float("\n🌐 Derinlik (km): ")
    mw = _ask_float("🔢 Moment büyüklüğü (Mw): ")
    run(mw, depth, eq_lat, eq_lon, sites)


def run(mw, depth, eq_lat, eq_lon, sites, html="deprem_haritasi.html", open_browser=True):
    t = point_source_table(mw, depth, eq_lat, eq_lon, sites)
    for i in range(len(sites)):
        label, _ = describe(t["allen"][i])
        print(f"\n👤 Konum {i + 1}")
        print(f"  {'Episantral uzaklık':<28}: {t['repi'][i]:.1f} km")
        print(f"  {'Hiposantral uzaklık':<28}: {t['rhyp'][i]:.1f} km")
        print(f"  {'Allen vd. 2012 (Rhyp)':<28}: {t['allen'][i]:.2f} ± {t['allen_sd'][i]:.2f} → {to_roman(t['allen'][i])} ({label})")
        print(f"  {'Bayrak vd. 2019 (R3)':<28}: {t['bayrak'][i]:.2f} ± {t['bayrak_sd'][i]:.2f} → {to_roman(t['bayrak'][i])}")
        print(f"  {'Eski formül (doğrulanmamış)':<28}: {t['legacy'][i]:.2f}")
    try:
        from .mapping import simple_map
    except ImportError:
        return t
    m = simple_map(eq_lat, eq_lon, t)
    m.save(html)
    print(f"\n🗺️  Harita kaydedildi: {html}")
    if open_browser:
        webbrowser.open(html)
    return t


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="MMI Intensity Mapper")
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    try:
        interactive()
    except ValueError as e:
        print(f"⚠️ Hata: {e}")


if __name__ == "__main__":
    main()
