"""Streamlit arayüzü:  streamlit run app/streamlit_app.py"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mmi_mapper import events as E  # noqa: E402
from mmi_mapper.exposure import exposure  # noqa: E402
from mmi_mapper.grid import run_latlon_grid  # noqa: E402
from mmi_mapper.mapping import layered_map  # noqa: E402
from mmi_mapper.model import MODEL_LABELS, Event, run_scenario  # noqa: E402
from mmi_mapper.rupture import build_rupture  # noqa: E402
from mmi_mapper.scale import describe, to_roman  # noqa: E402
from mmi_mapper.site import assign_vs30  # noqa: E402
from mmi_mapper.uncertainty import LogicTree, add_uncertainty  # noqa: E402

st.set_page_config(page_title="MMI Intensity Mapper", page_icon="🌍", layout="wide")
st.title("🌍 MMI Intensity Mapper")
st.caption("Olmuş bir depremin farklı noktalarda nasıl hissedildiğini tahmin eder. Deprem *öngörüsü* yapmaz.")

CUSTOM = "Özel senaryo"
EVENTS = E.load_events()
PRESETS = {f"{r['name']} · Mw {r.mag:.1f}": (float(r.mag), float(r.lat), float(r.lon), float(r.depth_km), eid)
           for eid, r in EVENTS.iterrows()}
PRESETS[CUSTOM] = (6.5, 39.0, 35.0, 10.0, "senaryo")
GEOMETRY_OPTIONS = {"auto": "USGS fayı (ShakeMap / FFM)", "gem": "Otomatik GEM izi + Thingbaijam 2017",
                    "point": "Nokta kaynak"}

with st.sidebar:
    st.header("Deprem")
    preset = st.selectbox("Hazır senaryo", list(PRESETS))
    m0, la0, lo0, d0, eid = PRESETS[preset]
    is_event = eid in EVENTS.index
    # Anahtarlar senaryoya bağlı: senaryo değişince alanlar o depremin değerlerine döner
    mag = st.number_input("Mw", 4.0, 8.5, m0, 0.1, key=f"mag_{eid}")
    lat = st.number_input("Episantr enlemi", 33.0, 43.5, la0, 0.01, format="%.4f", key=f"lat_{eid}")
    lon = st.number_input("Episantr boylamı", 24.0, 46.0, lo0, 0.01, format="%.4f", key=f"lon_{eid}")
    depth = st.number_input("Derinlik (km)", 1.0, 100.0, d0, 1.0, key=f"depth_{eid}")
    edited = is_event and not np.allclose((mag, lat, lon, depth), (m0, la0, lo0, d0))

    st.header("Kaynak geometrisi")
    has_usgs_fault = is_event and E.rupture_file(eid, EVENTS) is not None and not edited
    geo_keys = (["auto"] if has_usgs_fault else []) + ["gem", "point"]
    default_geo = 0 if has_usgs_fault or mag >= 6.5 else geo_keys.index("point")
    geometry = st.radio("Fay", geo_keys, index=default_geo, format_func=GEOMETRY_OPTIONS.get, key=f"geo_{eid}")
    if is_event and not has_usgs_fault and not edited:
        st.caption("Bu deprem için kullanılabilir bir USGS fayı yok; otomatik GEM fayı kullanılır.")

    use_raster = st.checkbox("Vs30: USGS Global Vs30 rasteri", value=True)
    vs30 = None if use_raster else st.number_input("Sabit Vs30 (m/s)", 150.0, 1500.0, 760.0, 10.0)
    st.header("Mantık ağacı ağırlıkları")
    w = {k: st.slider(MODEL_LABELS[k], 0.0, 1.0, v, 0.05) for k, v in LogicTree().weights.items()}
    st.header("Harita")
    half = st.slider("Yarı genişlik (°)", 1.0, 4.0, 2.5, 0.5)
    step = st.select_slider("Izgara adımı (°)", [0.1, 0.05, 0.025], 0.05)

if sum(w.values()) <= 0:
    st.error("Mantık ağacında en az bir dalın ağırlığı sıfırdan büyük olmalı.")
    st.stop()
if edited:
    st.warning("Parametreler hazır senaryodan farklı: USGS fayı ve gözlemler bu senaryoya uygulanmıyor.")

ev = Event(mag, lat, lon, depth, event_id=eid if not edited else "senaryo")
tree = LogicTree(weights=w)


@st.cache_resource(show_spinner=False)
def get_rupture(mag, lat, lon, depth, geometry, eid):
    if geometry == "auto":
        return build_rupture(mag, lat, lon, depth, rupture_geojson=E.rupture_file(eid, EVENTS))
    return build_rupture(mag, lat, lon, depth, use_finite=geometry == "gem")


@st.cache_data(show_spinner="Hesaplanıyor…")
def compute(mag, lat, lon, depth, eid, geometry, vs30, wt, half, step):
    e = Event(mag, lat, lon, depth, event_id=eid)
    rup = get_rupture(mag, lat, lon, depth, geometry, eid)
    t = LogicTree(weights=dict(wt))
    g, _ = run_latlon_grid(e, half, step, vs30=vs30, tree=t, rupture=rup)
    table, places, _ = exposure(e, half + 0.5, tree=t, vs30=vs30, rupture=rup)
    return g, table, places


@st.cache_data(show_spinner="Gözlemler hesaplanıyor…")
def compute_observations(eid, geometry, wt):
    """Gözlem noktalarında tahmin; Vs30 benchmark'taki gibi gözlemdeki değer, yoksa raster."""
    obs = E.usgs_observations(eid).reset_index(drop=True)
    if obs.empty:
        return obs
    ev_ = E.get_event(eid, EVENTS)
    rup = get_rupture(ev_.mag, ev_.lat, ev_.lon, ev_.depth, geometry, eid)
    v, _ = assign_vs30(obs.lat.to_numpy(), obs.lon.to_numpy())
    if "vs30" in obs:
        v = np.where(np.isfinite(obs.vs30.to_numpy(float)), obs.vs30.to_numpy(float), v)
    o, _ = run_scenario(ev_, obs.lat.to_numpy(), obs.lon.to_numpy(), vs30=v, rupture=rup)
    o = add_uncertainty(o, LogicTree(weights=dict(wt)), finite=rup.is_finite)
    cols = [k for k in MODEL_LABELS if k in o] + ["lt_mean", "lt_p16", "lt_p50", "lt_p84", "rrup"]
    return pd.concat([obs.drop(columns=["rrup"], errors="ignore"), o[cols]], axis=1)


def residual_table(obs: pd.DataFrame) -> pd.DataFrame:
    """Gözlem türü × model: sapma (gözlem − tahmin) ve RMSE."""
    models = {**{k: MODEL_LABELS[k] for k in MODEL_LABELS if k in obs}, "lt_mean": "Mantık ağacı (ortalama)"}
    rows = []
    for grp, d in [("Tümü", obs), *obs.groupby("obs_type")]:
        row = {"Gözlem türü": grp, "N": len(d)}
        for k, label in models.items():
            r = d.obs_mmi - d[k]
            row[label] = f"{r.mean():+.2f} · {np.sqrt((r ** 2).mean()):.2f}"
        rows.append(row)
    return pd.DataFrame(rows)


wt = tuple(w.items())
g, table, places = compute(mag, lat, lon, depth, ev.event_id, geometry, vs30, wt, half, step)
rup = get_rupture(mag, lat, lon, depth, geometry, ev.event_id)
obs = compute_observations(eid, geometry, wt) if is_event and not edited else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Kaynak", "Sonlu fay" if rup.is_finite else "Nokta kaynak",
          f"L = {rup.length:.0f} km" if rup.is_finite else None)
c2.metric("Maks. medyan MMI", f"{to_roman(g.lt_p50.max())} ({g.lt_p50.max():.1f})")
c3.metric("MMI ≥ VII'ye maruz nüfus (medyan)",
          f"{table.loc[table.MMI.isin(['VII', 'VIII', 'IX', 'X+']), 'Medyan'].sum():,.0f}")
if obs is not None and len(obs):
    r = obs.obs_mmi - obs.lt_mean
    c4.metric("Gözlemlere karşı RMSE", f"{np.sqrt((r ** 2).mean()):.2f} MMI", f"sapma {r.mean():+.2f}",
              delta_color="off", help=f"{len(obs)} gözlem; mantık ağacı ortalaması")
st.caption(f"Fay kaynağı: {rup.source}")

tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Harita", "👥 Nüfus maruziyeti", "📍 Nokta sorgusu", "📊 Gözlemler"])
with tab1:
    html = layered_map(ev, g, rup, obs, places).get_root().render()
    if hasattr(st, "iframe"):
        st.iframe(html, height=620)
    else:  # eski Streamlit sürümleri
        import streamlit.components.v1 as components

        components.html(html, height=620)
    st.caption("Katmanlar sağ üstten açılıp kapatılabilir: medyan, %16, %84, σ, P(≥VII), P(≥VIII), fay, gözlem, yerleşim.")
with tab2:
    st.dataframe(table.style.format({"%16": "{:,.0f}", "Medyan": "{:,.0f}", "%84": "{:,.0f}"}), hide_index=True)
    st.caption("PAGER mantığı; nüfus GeoNames ≥ 15 000 yerleşimlerinden (kırsal nüfus hariç).")
    st.dataframe(places.head(25)[["name", "population", "rrup", "lt_p16", "lt_p50", "lt_p84", "p_ge_8"]],
                 hide_index=True)
with tab3:
    q_lat = st.number_input("Enlem", value=lat + 0.3, format="%.4f")
    q_lon = st.number_input("Boylam", value=lon + 0.3, format="%.4f")
    d, _ = run_scenario(ev, [q_lat], [q_lon], vs30=vs30, rupture=rup)
    d = add_uncertainty(d, tree, finite=rup.is_finite).iloc[0]
    st.write(f"Repi {d.repi:.1f} km · Rjb {d.rjb:.1f} km · Rrup {d.rrup:.1f} km · Vs30 {d.vs30:.0f} m/s")
    st.dataframe(pd.DataFrame([{"model": MODEL_LABELS[k], "medyan": d[k],
                                "σ": d.get(f"{k}_sd", np.nan)} for k in MODEL_LABELS]), hide_index=True)
    st.success(f"Mantık ağacı: {d.lt_p16:.2f} / {d.lt_p50:.2f} / {d.lt_p84:.2f} → {to_roman(d.lt_p50)} "
               f"({describe(d.lt_p50)[0]}) · P(≥VII) {d.p_ge_7:.0%} · P(≥VIII) {d.p_ge_8:.0%}")
with tab4:
    if obs is None or not len(obs):
        st.info("Bu senaryo için gözlem yok. Gözlemler yalnızca hazır depremler, parametreleri değiştirilmeden "
                "seçildiğinde gösterilir.")
    else:
        st.markdown("**Sapma · RMSE (MMI)** — sapma = gözlem − tahmin; negatif değer fazla tahmin demektir.")
        st.dataframe(residual_table(obs), hide_index=True)
        st.caption("Kaynak: USGS ComCat (DYFI, ShakeMap istasyonları, makrosismik saha şiddetleri). "
                   "Enstrümantal gözlemlerde PGV, Worden vd. (2012) ile MMI'ya çevrildi.")
        show = [c for c in ["obs_type", "source", "station", "lat", "lon", "rrup", "pgv_cms", "n_resp", "obs_mmi",
                            "lt_p16", "lt_p50", "lt_p84"] if c in obs]
        st.dataframe(obs[show].sort_values("rrup"), hide_index=True)
