"""Aşama 3 — doğrulama benchmark'ı.

    python scripts/run_benchmark.py

Gözlem kümeleri
---------------
1. Kahramanmaraş 2023 (us6000jllz Mw 7.8, us6000jlqa Mw 7.5): USGS DYFI + ShakeMap'teki AFAD ve KOERI istasyonları.
2. Altı büyük deprem (Kahramanmaraş ×2, Elazığ 2020, Sisam 2020, Düzce 1999, İzmit 1999): DYFI, istasyonlar ve
   ShakeMap'teki makrosismik saha şiddetleri (data/observations/usgs_observations.csv, data/events.csv).
3. Türkiye Mw ≥ 6.0 depremleri (KOERI tablosu).
4. Tüm KOERI kayıtları (Mw 4.3–7.8) — Aşama 4'teki ML modeli bu artık tablosunu kullanır.

Ek gözlemler: data/raw/<event_id>/afad_stations.csv (TADAS) ve field_map.csv (saha haritası) varsa eklenir.
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
from mmi_mapper import events as E  # noqa: E402
from mmi_mapper import observations as O  # noqa: E402
from mmi_mapper.model import Event  # noqa: E402

RES = ROOT / "results"
KAHRAMANMARAS = ["us6000jllz", "us6000jlqa"]
SHOW = ("legacy", "allen2012_rrup", "bayrak2019", "kale2015_wgrw12", "lt_mean")

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def event_from_koeri(d: pd.DataFrame, eid: str) -> Event:
    r = d[d.event_id == eid].iloc[0]
    return Event(mag=float(r.mw), lat=float(r.ev_lat), lon=float(r.ev_lon), depth=float(r.ev_depth_km), event_id=eid)


usgs_events = E.load_events


def run_usgs_events(event_ids, geometry="auto"):
    """``geometry``: 'auto' (data/events.csv'deki seçim), 'gem' (GEM + Thingbaijam) ya da 'point'."""
    evs = E.load_events()
    parts, rups = [], {}
    for eid in event_ids:
        ev = E.get_event(eid, evs)
        rup = E.event_rupture(eid, geometry, evs)
        res, rup = B.predict_for_observations(ev, E.usgs_observations(eid), rupture=rup)
        res["event_id"], res["event"] = eid, evs.loc[eid, "name"]
        parts.append(res)
        rups[eid] = rup
    return pd.concat(parts, ignore_index=True), rups


def run_koeri_events(koeri: pd.DataFrame, event_ids) -> pd.DataFrame:
    parts = []
    for eid in event_ids:
        ev = event_from_koeri(koeri, eid)
        res, _ = B.predict_for_observations(ev, O.load_koeri(event_id=eid))
        res["event_id"] = eid
        parts.append(res)
    return pd.concat(parts, ignore_index=True)


def md_table(df: pd.DataFrame, cols=("model", "N", "sapma", "RMSE", "MAE")) -> str:
    d = df[list(cols)].copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(f"{v:+.2f}" if k == "sapma" else f"{v:.2f}" if isinstance(v, float) else str(v)
                                       for k, v in r.items()) + " |")
    return "\n".join(lines)


def shown(m: pd.DataFrame) -> pd.DataFrame:
    return m[m.model.isin([B.LABELS[k] for k in SHOW])]


def geometry_table(event_ids, near_ref: pd.DataFrame) -> pd.DataFrame:
    """Aynı gözlemler, üç geometri. Yakın alan: seçili (USGS/otomatik) faya Rjb ≤ 50 km."""
    near = near_ref.rjb.to_numpy() <= 50
    rows = []
    for geom, lab in (("point", "Nokta kaynak"), ("gem", "GEM izi + Thingbaijam 2017 (otomatik)"),
                      ("auto", "USGS fayı (ShakeMap / FFM; yoksa GEM)")):
        r_, _ = run_usgs_events(event_ids, geometry=geom)
        for m in ("allen2012_rrup", "kale2015_wgrw12", "lt_mean"):
            rr = r_[f"res_{m}"].to_numpy()
            rows.append(dict(geometri=lab, model=B.LABELS[m], N=len(rr), sapma=float(rr.mean()),
                             RMSE=float(np.sqrt((rr**2).mean())), N_yakın=int(near.sum()),
                             RMSE_yakın=float(np.sqrt((rr[near] ** 2).mean()))))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main():
    RES.mkdir(exist_ok=True)
    koeri = pd.read_csv(O.KOERI)
    evs = usgs_events()
    summary = ["# Benchmark sonuçları", "",
               "Otomatik üretilmiştir: `python scripts/run_benchmark.py`. Artık = gözlem − tahmin (MMI);",
               "negatif sapma modelin fazla tahmin ettiğini gösterir. Enstrümantal gözlemlerde PGV, Worden vd. (2012)",
               "ile MMI'ya çevrilmiştir. Vs30 tüm noktalarda USGS Global Vs30 rasterinden alınmıştır.", ""]

    # 1) Kahramanmaraş -------------------------------------------------------
    km, rups = run_usgs_events(KAHRAMANMARAS)
    km.to_csv(RES / "residuals_kahramanmaras.csv", index=False, float_format="%.4f")
    m_km = B.metrics(km)
    m_km.to_csv(RES / "metrics_kahramanmaras.csv", index=False, float_format="%.3f")
    m_src = B.metrics(km, "source")
    m_src.to_csv(RES / "metrics_kahramanmaras_by_source.csv", index=False, float_format="%.3f")
    km["uzaklık"] = pd.cut(km.rrup, B.DIST_BINS)
    B.metrics(km, "uzaklık").to_csv(RES / "metrics_kahramanmaras_by_distance.csv", index=False, float_format="%.3f")
    B.plot_residuals(km, RES / "residual_distance_kahramanmaras.png",
                     "Kahramanmaraş 2023 (Mw 7.8 + 7.5) — artık vs. Rrup")
    geo = geometry_table(KAHRAMANMARAS, km)
    geo.to_csv(RES / "geometry_sensitivity_kahramanmaras.csv", index=False, float_format="%.3f")
    srcs = ", ".join(f"{k}: {v}" for k, v in km.source.value_counts().items())
    summary += ["## 1. Kahramanmaraş 2023", "", f"Gözlemler: {srcs}.", "",
                *(f"- {eid} ({evs.loc[eid, 'name']}): {r.source}, L = {r.length:.0f} km" for eid, r in rups.items()),
                "", md_table(m_km), "", "### Gözlem türüne göre", "",
                md_table(shown(m_src), cols=("grup", "model", "N", "sapma", "RMSE")), "",
                "![](residual_distance_kahramanmaras.png)", "",
                "### Kaynak geometrisi duyarlılığı", "",
                "Aynı gözlemler, üç kaynak geometrisiyle. `RMSE_yakın`: USGS fayına Rjb ≤ 50 km olan noktalar.", "",
                md_table(geo, cols=("geometri", "model", "N", "sapma", "RMSE", "N_yakın", "RMSE_yakın")), ""]

    # 2) Altı büyük deprem ---------------------------------------------------
    six, rups6 = run_usgs_events(list(evs.index))
    six.to_csv(RES / "residuals_six_events.csv", index=False, float_format="%.4f")
    m6e = B.metrics(six)
    m6e.to_csv(RES / "metrics_six_events.csv", index=False, float_format="%.3f")
    by_ev = B.metrics(six, "event")
    by_ev.to_csv(RES / "metrics_six_events_by_event.csv", index=False, float_format="%.3f")
    by_type = B.metrics(six, "obs_type")
    by_type.to_csv(RES / "metrics_six_events_by_obs_type.csv", index=False, float_format="%.3f")
    piv = shown(by_ev).pivot(index="grup", columns="model", values="RMSE")[[B.LABELS[k] for k in SHOW]]
    n_ev = six.groupby("event").size()
    piv.insert(0, "N", n_ev)
    piv = piv.loc[[evs.loc[e, "name"] for e in evs.index]]
    piv.round(3).to_csv(RES / "rmse_by_event.csv")
    geo6 = geometry_table(list(evs.index), six)
    geo6.to_csv(RES / "geometry_sensitivity_six_events.csv", index=False, float_format="%.3f")
    B.plot_residuals(six, RES / "residual_distance_six_events.png",
                     f"Altı büyük deprem ({len(six)} gözlem) — artık vs. Rrup")
    B.plot_residuals(six, RES / "residual_vs30_six_events.png", "Altı büyük deprem — artık vs. Vs30",
                     xcol="vs30", xlabel="Vs30 (m/s)")
    ev_lines = [f"- {evs.loc[e, 'name']} (Mw {evs.loc[e, 'mag']}, `{e}`): {rups6[e].source}, "
                f"L = {rups6[e].length:.0f} km; " + ", ".join(f"{k}: {v}" for k, v in
                                                           six[six.event_id == e].source.value_counts().items())
                for e in evs.index]
    piv_md = ["| Deprem | N | " + " | ".join(piv.columns[1:]) + " |", "|---" * (len(piv.columns) + 1) + "|"]
    piv_md += [f"| {i} | {int(r.N)} | " + " | ".join(f"{v:.2f}" for v in r.iloc[1:]) + " |" for i, r in piv.iterrows()]
    summary += [f"## 2. Altı büyük deprem ({len(six)} gözlem)", "",
                "Fay seçimi: ShakeMap `rupture.json` → USGS FFM → GEM otomatik. Bir USGS dosyası, uzunluğu",
                "Thingbaijam vd. (2017) medyanının en az yarısıysa kabul edilir (bazı eski ShakeMap Atlas fayları",
                "yalnızca 5–20 km'lik tek parçadır).", "", *ev_lines, "",
                md_table(m6e), "", "### Deprem bazında RMSE", "", *piv_md, "",
                "### Gözlem türüne göre", "", md_table(shown(by_type), cols=("grup", "model", "N", "sapma", "RMSE")), "",
                "### Kaynak geometrisi duyarlılığı (altı deprem)", "",
                md_table(geo6, cols=("geometri", "model", "N", "sapma", "RMSE", "N_yakın", "RMSE_yakın")), "",
                "![](residual_distance_six_events.png)", "", "![](residual_vs30_six_events.png)", ""]

    # 3) KOERI Mw >= 6 -------------------------------------------------------
    big = sorted(koeri[koeri.mw >= 6.0].event_id.unique())
    m6 = run_koeri_events(koeri, big)
    m6.to_csv(RES / "residuals_m6.csv", index=False, float_format="%.4f")
    m_m6 = B.metrics(m6)
    m_m6.to_csv(RES / "metrics_m6.csv", index=False, float_format="%.3f")
    B.plot_residuals(m6, RES / "residual_distance_m6.png", f"Türkiye Mw ≥ 6.0 ({len(big)} deprem, KOERI) — artık vs. Rrup")
    B.plot_obs_vs_pred(m6, RES / "obs_vs_pred_m6.png", "Türkiye Mw ≥ 6.0 — gözlem vs. tahmin")
    summary += [f"## 3. Türkiye Mw ≥ 6.0 — KOERI ({len(big)} deprem, {len(m6)} kayıt)", "",
                "Fay: Mw ≥ 6.5 için GEM otomatik, daha küçükler nokta kaynak. PGV geometrik ortalama.", "",
                md_table(m_m6), "", "![](residual_distance_m6.png)", "", "![](obs_vs_pred_m6.png)", ""]

    # 4) Tüm KOERI -----------------------------------------------------------
    allres = run_koeri_events(koeri, sorted(koeri.event_id.unique()))
    allres.to_csv(RES / "residuals_koeri_all.csv", index=False, float_format="%.4f")
    m_all = B.metrics(allres)
    m_all.to_csv(RES / "metrics_koeri_all.csv", index=False, float_format="%.3f")
    allres["uzaklık"] = pd.cut(allres.rrup, B.DIST_BINS)
    B.metrics(allres, "uzaklık").to_csv(RES / "metrics_koeri_all_by_distance.csv", index=False, float_format="%.3f")
    B.plot_residuals(allres, RES / "residual_distance_koeri_all.png",
                     f"Tüm KOERI kayıtları ({allres.event_id.nunique()} deprem, Mw 4.3–7.8) — artık vs. Rrup")
    B.plot_residuals(allres, RES / "residual_vs30_koeri_all.png", "Tüm KOERI kayıtları — artık vs. Vs30",
                     xcol="vs30", xlabel="Vs30 (m/s)")
    summary += [f"## 4. Tüm KOERI kayıtları ({allres.event_id.nunique()} deprem, {len(allres)} kayıt)", "",
                md_table(m_all), "", "![](residual_distance_koeri_all.png)", "", "![](residual_vs30_koeri_all.png)", ""]

    # 5) Duyarlılık: enstrümantal gözlemin GMICE seçimi ----------------------
    sens = []
    for name, d in (("Altı deprem (enstrümantal)", six[six.obs_type == "enstrümantal"]), ("KOERI Mw ≥ 6", m6),
                    ("Tüm KOERI", allres)):
        for m in ("allen2012_rrup", "kale2015_wgrw12", "kale2015_ba14", "lt_mean"):
            for obs_col, lab in (("obs_mmi", "WGRW12"), ("obs_mmi_ba14", "Bilal & Askan")):
                r = d[obs_col] - d[m]
                sens.append(dict(küme=name, model=B.LABELS[m], gözlem_GMICE=lab, N=len(r), sapma=r.mean(),
                                 RMSE=float(np.sqrt((r**2).mean()))))
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_observed_gmice.csv", index=False, float_format="%.3f")
    summary += ["## 5. Duyarlılık: enstrümantal gözlemin GMICE seçimi", "",
                "Enstrümantal 'gözlem' de bir dönüşüm denklemine bağlıdır. Aynı PGV kayıtları WGRW12 ve",
                "Bilal & Askan 2014 ile MMI'ya çevrildiğinde metrikler aşağıdaki gibi değişir.", "",
                md_table(sens[sens.küme != "Tüm KOERI"], cols=("küme", "model", "gözlem_GMICE", "N", "sapma", "RMSE")),
                ""]
    summary += ["## Sınırlamalar", "",
                "- ShakeMap istasyon PGV'leri büyük yatay bileşendir; Kale 2015 geometrik ortalama verir (≈0,1–0,3 MMI).",
                "- Makrosismik saha şiddetleri ShakeMap'teki haliyle kullanıldı (1999 depremlerinin gözlenen",
                "  şiddetleri, Sisam 2020 için EMSC); ölçek dönüşümü uygulanmadı.",
                "- Düzce 1999 için USGS FFM yok ve ShakeMap Atlas fayı 5 km'lik tek parça; GEM otomatik fay kullanıldı.",
                "- Albayrak vd. (2024) saha haritası ve TADAS tabloları dahil değildir (`data/raw/<event_id>/`).",
                "- KOERI veri setinin PGA'ları kaynak belgesine göre Akkar vd. (2014)'e kıyasla log10'da ~0,24 düşüktür.",
                "- Bayrak 2019, MMI ≥ 4 ve Mw ≥ 4.5 için türetilmiştir; tüm-KOERI kümesinin çoğu bu aralığın dışındadır.",
                ""]
    (RES / "README.md").write_text("\n".join(summary))
    print("\n".join(summary))


if __name__ == "__main__":
    main()
