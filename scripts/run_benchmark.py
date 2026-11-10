"""Aşama 3 — doğrulama benchmark'ı.

    python scripts/run_benchmark.py

Üç gözlem kümesi:
1. Kahramanmaraş 2023 (us6000jllz Mw 7.8, us6000jlqa Mw 7.5): KOERI istasyonları +
   data/raw/<event_id>/ altında bulunursa USGS DYFI, ShakeMap istasyonları (AFAD = ağ kodu TK),
   elle indirilen AFAD CSV'si ve saha haritası.
2. Türkiye Mw ≥ 6.0 depremleri (KOERI).
3. Tüm KOERI kayıtları (Mw 4.3–7.8) — Aşama 4'teki ML modeli bu artık tablosunu kullanır.

Çıktılar results/ klasörüne yazılır.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mmi_mapper import benchmark as B  # noqa: E402
from mmi_mapper import observations as O  # noqa: E402
from mmi_mapper.model import Event  # noqa: E402

RES = ROOT / "results"
RAW = ROOT / "data" / "raw"
KAHRAMANMARAS = {"us6000jllz": "Pazarcık Mw 7.8", "us6000jlqa": "Elbistan Mw 7.5"}

warnings.filterwarnings("ignore")


def event_from_koeri(d: pd.DataFrame, eid: str) -> Event:
    r = d[d.event_id == eid].iloc[0]
    return Event(mag=float(r.mw), lat=float(r.ev_lat), lon=float(r.ev_lon), depth=float(r.ev_depth_km), event_id=eid)


USGS_OBS = ROOT / "data" / "observations" / "usgs_observations.csv"
RUPTURES = ROOT / "data" / "ruptures"


def extra_observations(eid: str) -> list[pd.DataFrame]:
    """KOERI dışındaki gözlemler.

    * data/observations/usgs_observations.csv — USGS DYFI ve ShakeMap'teki AFAD istasyonları
      (scripts/build_usgs_observations.py ile üretilir).
    * data/raw/<eid>/afad_stations.csv — TADAS'tan elle indirilen AFAD tablosu (varsa).
    * data/raw/<eid>/field_map.csv — saha araştırması şiddetleri (varsa).
    """
    out = []
    if USGS_OBS.exists():
        u = pd.read_csv(USGS_OBS)
        u = u[u.event_id == eid].drop(columns=["event_id"])
        if len(u):
            out.append(u)
    folder = RAW / eid
    if (folder / "afad_stations.csv").exists():
        out.append(O.load_afad_csv(folder / "afad_stations.csv"))
    if (folder / "field_map.csv").exists():
        out.append(O.load_field_map(folder / "field_map.csv"))
    return out


def rupture_file(eid: str):
    """ShakeMap'in operasyonel sonlu fayı; yoksa USGS FFM; o da yoksa None (GEM tabanlı otomatik fay)."""
    for p in (RUPTURES / f"{eid}_shakemap_rupture.json", RAW / eid / "shakemap_rupture.json",
              RAW / eid / "finite-fault_FFM.geojson"):
        if p.exists():
            return p
    return None


def run_events(koeri: pd.DataFrame, event_ids, with_extras=False, geometry="auto") -> tuple[pd.DataFrame, dict]:
    """``geometry``: 'auto' (USGS fayı varsa o, yoksa GEM), 'gem' (GEM + Thingbaijam) ya da 'point'."""
    from mmi_mapper.rupture import build_rupture

    parts, ruptures = [], {}
    for eid in event_ids:
        ev = event_from_koeri(koeri, eid)
        obs = [O.load_koeri(event_id=eid)]
        if with_extras:
            obs += extra_observations(eid)
        obs = pd.concat(obs, ignore_index=True)
        if geometry == "point":
            rup = build_rupture(ev.mag, ev.lat, ev.lon, ev.depth, use_finite=False)
        elif geometry == "gem":
            rup = build_rupture(ev.mag, ev.lat, ev.lon, ev.depth)
        else:
            rup = build_rupture(ev.mag, ev.lat, ev.lon, ev.depth, rupture_geojson=rupture_file(eid))
        res, rup = B.predict_for_observations(ev, obs, rupture=rup)
        res["event_id"] = eid
        parts.append(res)
        ruptures[eid] = rup
    return pd.concat(parts, ignore_index=True), ruptures


def md_table(df: pd.DataFrame, cols=("model", "N", "sapma", "RMSE", "MAE")) -> str:
    d = df[list(cols)].copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(f"{v:+.2f}" if k == "sapma" else f"{v:.2f}" if isinstance(v, float) else str(v)
                                       for k, v in r.items()) + " |")
    return "\n".join(lines)


def main():
    RES.mkdir(exist_ok=True)
    koeri = pd.read_csv(O.KOERI)
    summary = ["# Benchmark sonuçları", "",
               "Otomatik üretilmiştir: `python scripts/run_benchmark.py`. Artık = gözlem − tahmin (MMI).",
               "Enstrümantal gözlemler PGV'den Worden vd. (2012) ile MMI'ya çevrilmiştir.", ""]

    # 1) Kahramanmaraş
    km, rups = run_events(koeri, KAHRAMANMARAS, with_extras=True)
    km.to_csv(RES / "residuals_kahramanmaras.csv", index=False, float_format="%.4f")
    m_km = B.metrics(km)
    m_km.to_csv(RES / "metrics_kahramanmaras.csv", index=False, float_format="%.3f")
    B.plot_residuals(km, RES / "residual_distance_kahramanmaras.png",
                     "Kahramanmaraş 2023 (Mw 7.8 + 7.5) — artık vs. Rrup")
    srcs = ", ".join(f"{k}: {v}" for k, v in km.source.value_counts().items())
    m_src = B.metrics(km, "source")
    m_src.to_csv(RES / "metrics_kahramanmaras_by_source.csv", index=False, float_format="%.3f")
    km["uzaklık"] = pd.cut(km.rrup, B.DIST_BINS)
    B.metrics(km, "uzaklık").to_csv(RES / "metrics_kahramanmaras_by_distance.csv", index=False, float_format="%.3f")
    summary += ["## 1. Kahramanmaraş 2023", "", f"Gözlemler: {srcs}.", "",
                "DYFI: `cdi_geo.txt`, en az 3 yanıt, şüpheli hücreler hariç. AFAD: ShakeMap istasyon listesindeki TK",
                "ağı istasyonları (aykırı işaretliler hariç; PGV büyük yatay bileşen). Vs30: istasyonlarda ShakeMap/KOERI",
                "değeri, DYFI hücrelerinde ShakeMap listesindeki en yakın noktanın (≤ 7 km) değeri.", "",
                *(f"- {eid} ({KAHRAMANMARAS[eid]}): {r.source}, L = {r.length:.0f} km" for eid, r in rups.items()),
                "", md_table(m_km), "", "### Gözlem türüne göre", "",
                md_table(m_src[m_src.model.isin([B.LABELS[m] for m in ("legacy", "allen2012_rrup", "bayrak2019",
                                                                       "kale2015_wgrw12", "lt_mean")])],
                         cols=("grup", "model", "N", "sapma", "RMSE")),
                "", "![](residual_distance_kahramanmaras.png)", ""]

    # 1b) Kaynak geometrisi duyarlılığı (aynı gözlemler)
    geo_rows = []
    for geom, lab in (("point", "Nokta kaynak"), ("gem", "GEM izi + Thingbaijam 2017 (otomatik)"),
                      ("auto", "USGS ShakeMap fayı")):
        r_, _ = run_events(koeri, KAHRAMANMARAS, with_extras=True, geometry=geom)
        for m in ("allen2012_rrup", "kale2015_wgrw12", "lt_mean"):
            rr = r_[f"res_{m}"]
            near = rr[km.rjb.to_numpy() <= 50]
            geo_rows.append(dict(geometri=lab, model=B.LABELS[m], N=len(rr), sapma=rr.mean(),
                                 RMSE=float(np.sqrt((rr**2).mean())),
                                 RMSE_fay_50km=float(np.sqrt((near**2).mean()))))
    geo = pd.DataFrame(geo_rows)
    geo.to_csv(RES / "geometry_sensitivity_kahramanmaras.csv", index=False, float_format="%.3f")
    summary += ["### Kaynak geometrisi duyarlılığı", "",
                "Aynı gözlemler, üç kaynak geometrisiyle. `RMSE_fay_50km`: USGS fayına Rjb ≤ 50 km olan noktalar.", "",
                md_table(geo, cols=("geometri", "model", "N", "sapma", "RMSE", "RMSE_fay_50km")), ""]

    # 2) Mw >= 6
    big = sorted(koeri[koeri.mw >= 6.0].event_id.unique())
    m6, _ = run_events(koeri, big)
    m6.to_csv(RES / "residuals_m6.csv", index=False, float_format="%.4f")
    m_m6 = B.metrics(m6)
    m_m6.to_csv(RES / "metrics_m6.csv", index=False, float_format="%.3f")
    B.plot_residuals(m6, RES / "residual_distance_m6.png", f"Türkiye Mw ≥ 6.0 ({len(big)} deprem, KOERI) — artık vs. Rrup")
    B.plot_obs_vs_pred(m6, RES / "obs_vs_pred_m6.png", "Türkiye Mw ≥ 6.0 — gözlem vs. tahmin")
    summary += [f"## 2. Türkiye Mw ≥ 6.0 ({len(big)} deprem, {len(m6)} kayıt)", "", md_table(m_m6), "",
                "![](residual_distance_m6.png)", "", "![](obs_vs_pred_m6.png)", ""]

    # 3) Tüm KOERI
    allres, _ = run_events(koeri, sorted(koeri.event_id.unique()))
    allres.to_csv(RES / "residuals_koeri_all.csv", index=False, float_format="%.4f")
    m_all = B.metrics(allres)
    m_all.to_csv(RES / "metrics_koeri_all.csv", index=False, float_format="%.3f")
    allres["uzaklık"] = pd.cut(allres.rrup, B.DIST_BINS)
    m_bin = B.metrics(allres, "uzaklık")
    m_bin.to_csv(RES / "metrics_koeri_all_by_distance.csv", index=False, float_format="%.3f")
    B.plot_residuals(allres, RES / "residual_distance_koeri_all.png",
                     f"Tüm KOERI kayıtları ({allres.event_id.nunique()} deprem, Mw 4.3–7.8) — artık vs. Rrup")
    B.plot_residuals(allres, RES / "residual_vs30_koeri_all.png", "Tüm KOERI kayıtları — artık vs. Vs30",
                     xcol="vs30", xlabel="Vs30 (m/s)")
    summary += [f"## 3. Tüm KOERI kayıtları ({allres.event_id.nunique()} deprem, {len(allres)} kayıt)", "",
                md_table(m_all), "", "![](residual_distance_koeri_all.png)", "", "![](residual_vs30_koeri_all.png)", ""]

    # 4) Duyarlılık: gözlemleri Bilal & Askan 2014 ile tanımlamak
    sens = []
    for name, d in (("Kahramanmaraş (enstrümantal)", km[km.obs_type == "enstrümantal"]), ("Mw ≥ 6", m6),
                    ("Tüm KOERI", allres)):
        for m in ("allen2012_rrup", "kale2015_wgrw12", "kale2015_ba14", "lt_mean"):
            for obs_col, lab in (("obs_mmi", "WGRW12"), ("obs_mmi_ba14", "Bilal & Askan")):
                r = d[obs_col] - d[m]
                sens.append(dict(küme=name, model=B.LABELS[m], gözlem_GMICE=lab, N=len(r), sapma=r.mean(),
                                 RMSE=float(np.sqrt((r**2).mean()))))
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_observed_gmice.csv", index=False, float_format="%.3f")
    summary += ["## 4. Duyarlılık: enstrümantal gözlemin GMICE seçimi", "",
                "Enstrümantal 'gözlem' de bir dönüşüm denklemine bağlıdır. Aşağıdaki tablo aynı PGV kayıtlarının",
                "WGRW12 ve Bilal & Askan 2014 ile MMI'ya çevrilmesinin metrikleri nasıl değiştirdiğini gösterir.", "",
                md_table(sens[sens.küme != "Tüm KOERI"], cols=("küme", "model", "gözlem_GMICE", "N", "sapma", "RMSE")),
                ""]
    summary += ["## Sınırlamalar", "",
                "- AFAD gözlemleri ShakeMap istasyon listesindeki PGV'lerdir (büyük yatay bileşen); Kale 2015 geometrik",
                "  ortalama verir. Bu fark Kale zincirinin AFAD'a karşı pozitif sapmasının (~0,1–0,3 MMI) bir kısmını açıklar.",
                "- ShakeMap istasyon listesindeki AFAD istasyonlarının yaklaşık yarısında Vs30 = 760 m/s (ShakeMap'in",
                "  atadığı değer) görünür; bu, zemin büyütmesini düşük tahmin ettirebilir.",
                "- Albayrak vd. (2024) saha haritası ve TADAS tabloları henüz dahil değildir (`data/raw/<event_id>/`).",
                "- Kaynak veri setinin belgelerine göre KOERI PGA değerleri Akkar vd. (2014)'e kıyasla log10'da",
                "  ~0,24 düşüktür; bu, özellikle tüm-KOERI kümesindeki negatif sapmanın bir kısmını açıklayabilir.",
                "- Bayrak 2019, MMI ≥ 4 ve Mw ≥ 4.5 için türetilmiştir. Tüm-KOERI kümesindeki küçük depremler ve",
                "  düşük şiddetler bu aralığın dışındadır.",
                "- Enstrümantal gözlem GMICE'ye bağlıdır (bkz. bölüm 4); DYFI bu döngüselliği kırar.", ""]
    (RES / "README.md").write_text("\n".join(summary))
    print("\n".join(summary))


if __name__ == "__main__":
    main()
