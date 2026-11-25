"""Komut satırı arayüzü.

Etkileşimli:   mmi-mapper            (ya da python -m mmi_mapper)
Argümanlarla:  mmi-mapper --mag 7.8 --lat 37.226 --lon 37.014 --depth 10 \
                   --site 37.5753,36.9228 --site 36.2023,36.1613
Benchmark depremi (data/events.csv; USGS fayı varsa kullanılır):
               mmi-mapper --event us6000jllz --site 37.5753,36.9228
               mmi-mapper --list-events
"""

from __future__ import annotations

import argparse
import webbrowser

import numpy as np

from .coords import parse_coordinate
from .model import MODEL_LABELS, Event, run_scenario
from .scale import describe, to_roman
from .uncertainty import add_uncertainty


def _ask_float(prompt: str) -> float:
    return float(input(prompt).replace(",", "."))


def _interactive_inputs():
    print("\n📘 Episantral uzaklık: yüzeyde episantra olan uzaklık.")
    print("📘 Hiposantral uzaklık: depremin yer altındaki odağına (hiposantr) olan uzaklık.")
    print("📘 Rjb / Rrup: fayın yüzey izdüşümüne / fay yüzeyine en yakın uzaklık (Mw ≥ 6.5'te sonlu fay).\n")
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
    return Event(mag=mw, lat=eq_lat, lon=eq_lon, depth=depth), sites


def report(df, models=("allen2012_rrup", "bayrak2019", "kale2015_wgrw12", "legacy")) -> None:
    print(f"\nKaynak: {df.attrs.get('rupture_source')} | Vs30: {df.attrs.get('vs30_source')}")
    for i, r in df.reset_index(drop=True).iterrows():
        print(f"\n👤 Konum {i + 1}  ({r.lat:.4f}, {r.lon:.4f})")
        print(f"  Repi {r.repi:.1f} km · Rhyp {r.rhyp:.1f} km · Rjb {r.rjb:.1f} km · Rrup {r.rrup:.1f} km · Vs30 {r.vs30:.0f} m/s")
        for m in models:
            if m not in df:
                continue
            mu, sd = r[m], r.get(f"{m}_sd", np.nan)
            sd_txt = "" if np.isnan(sd) else f" ± {sd:.2f}"
            label = describe(mu)[0] if m != "legacy" else "doğrulanmamış"
            print(f"  {MODEL_LABELS[m]:<34}: {mu:5.2f}{sd_txt}  → {to_roman(mu)} ({label})")
        if "lt_p50" in df:
            print(f"  {'Mantık ağacı %16 / %50 / %84':<34}: {r.lt_p16:.2f} / {r.lt_p50:.2f} / {r.lt_p84:.2f}"
                  f"  → {to_roman(r.lt_p50)} ({describe(r.lt_p50)[0]})")
            print(f"  {'P(MMI ≥ VII) · P(MMI ≥ VIII)':<34}: {r.p_ge_7:.0%} · {r.p_ge_8:.0%}")


def run(event: Event, sites, vs30=None, html="deprem_haritasi.html", open_browser=True, rupture_geojson=None):
    lat = [s[0] for s in sites]
    lon = [s[1] for s in sites]
    df, rup = run_scenario(event, lat, lon, vs30=vs30, rupture_geojson=rupture_geojson)
    df = add_uncertainty(df, finite=rup.is_finite)
    report(df)
    if html:
        from .mapping import scenario_map

        scenario_map(event, df, rup).save(html)
        print(f"\n🗺️  Harita kaydedildi: {html}")
        if open_browser:
            webbrowser.open(html)
    return df, rup


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="MMI Intensity Mapper")
    p.add_argument("--event", default=None, help="data/events.csv'deki USGS olay kimliği (ör. us6000jllz)")
    p.add_argument("--list-events", action="store_true", help="hazır depremleri listele ve çık")
    p.add_argument("--mag", type=float)
    p.add_argument("--lat")
    p.add_argument("--lon")
    p.add_argument("--depth", type=float, default=10.0)
    p.add_argument("--rake", type=float, default=None)
    p.add_argument("--site", action="append", default=[], help="enlem,boylam (tekrarlanabilir)")
    p.add_argument("--vs30", type=float, default=None, help="tüm noktalar için sabit Vs30 (m/s)")
    p.add_argument("--rupture", default=None, help="3B fay GeoJSON'u (USGS FFM / ShakeMap rupture.json)")
    p.add_argument("--html", default="deprem_haritasi.html")
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    if a.list_events:
        from .events import load_events

        for eid, r in load_events().iterrows():
            print(f"{eid:<12} Mw {r.mag:.1f}  {r['name']:<32} fay: {r.rupture}")
        return
    try:
        if a.event is not None:
            from .events import get_event, load_events, rupture_file

            evs = load_events()
            if a.event not in evs.index:
                raise ValueError(f"Bilinmeyen olay: {a.event} (liste için --list-events)")
            event = get_event(a.event, evs)
            if a.rupture is None and rupture_file(a.event, evs) is not None:
                a.rupture = str(rupture_file(a.event, evs))
            sites = [tuple(parse_coordinate(v) for v in s.split(",")) for s in a.site]
            if not sites:
                raise ValueError("En az bir --site girin.")
        elif a.mag is None:
            event, sites = _interactive_inputs()
        else:
            event = Event(mag=a.mag, lat=parse_coordinate(a.lat), lon=parse_coordinate(a.lon), depth=a.depth, rake=a.rake)
            sites = [tuple(parse_coordinate(v) for v in s.split(",")) for s in a.site]
            if not sites:
                raise ValueError("En az bir --site girin.")
        run(event, sites, vs30=a.vs30, html=a.html, open_browser=not a.no_browser, rupture_geojson=a.rupture)
    except ValueError as e:
        print(f"⚠️ Hata: {e}")


if __name__ == "__main__":
    main()
