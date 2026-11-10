"""Streamlit arayüzü:  streamlit run app/streamlit_app.py"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mmi_mapper import observations as O  # noqa: E402
from mmi_mapper.exposure import exposure  # noqa: E402
from mmi_mapper.grid import run_latlon_grid  # noqa: E402
from mmi_mapper.mapping import layered_map  # noqa: E402
from mmi_mapper.model import MODEL_LABELS, Event, run_scenario  # noqa: E402
from mmi_mapper.scale import describe, to_roman  # noqa: E402
from mmi_mapper.uncertainty import LogicTree, add_uncertainty  # noqa: E402

st.set_page_config(page_title="MMI Intensity Mapper", page_icon="🌍", layout="wide")
st.title("🌍 MMI Intensity Mapper")
st.caption("Olmuş bir depremin farklı noktalarda nasıl hissedildiğini tahmin eder. Deprem *öngörüsü* yapmaz.")

PRESETS = {
    "Kahramanmaraş (Pazarcık) 2023 · Mw 7.8": (7.8, 37.2256, 37.0143, 10.0, "us6000jllz"),
    "Elbistan 2023 · Mw 7.5": (7.5, 38.0106, 37.1962, 7.4, "us6000jlqa"),
    "Sisam/İzmir 2020 · Mw 7.0": (7.0, 37.8973, 26.7838, 21.0, "us7000c7y0"),
    "Özel senaryo": (6.5, 39.0, 35.0, 10.0, "senaryo"),
}

with st.sidebar:
    st.header("Deprem")
    preset = st.selectbox("Hazır senaryo", list(PRESETS))
    m0, la0, lo0, d0, eid = PRESETS[preset]
    mag = st.number_input("Mw", 4.0, 8.5, m0, 0.1)
    lat = st.number_input("Episantr enlemi", 34.0, 43.0, la0, 0.01, format="%.4f")
    lon = st.number_input("Episantr boylamı", 25.0, 46.0, lo0, 0.01, format="%.4f")
    depth = st.number_input("Derinlik (km)", 1.0, 100.0, d0, 1.0)
    finite = st.checkbox("Sonlu fay (GEM izi + Thingbaijam 2017)", value=mag >= 6.5)
    use_raster = st.checkbox("Vs30: USGS Global Vs30 rasteri", value=True)
    vs30 = None if use_raster else st.number_input("Sabit Vs30 (m/s)", 150.0, 1500.0, 760.0, 10.0)
    st.header("Mantık ağacı ağırlıkları")
    w = {k: st.slider(MODEL_LABELS[k], 0.0, 1.0, v, 0.05) for k, v in LogicTree().weights.items()}
    st.header("Harita")
    half = st.slider("Yarı genişlik (°)", 1.0, 4.0, 2.5, 0.5)
    step = st.select_slider("Izgara adımı (°)", [0.1, 0.05, 0.025], 0.05)

ev = Event(mag, lat, lon, depth, event_id=eid)
tree = LogicTree(weights=w)


@st.cache_data(show_spinner="Hesaplanıyor…")
def compute(mag, lat, lon, depth, eid, finite, vs30, wt, half, step):
    from mmi_mapper.rupture import build_rupture

    e = Event(mag, lat, lon, depth, event_id=eid)
    rup = build_rupture(mag, lat, lon, depth, use_finite=finite)
    t = LogicTree(weights=dict(wt))
    g, _ = run_latlon_grid(e, half, step, vs30=vs30, tree=t, rupture=rup)
    table, places, _ = exposure(e, half + 0.5, tree=t, vs30=vs30, rupture=rup)
    return g, rup, table, places


g, rup, table, places = compute(mag, lat, lon, depth, eid, finite, vs30, tuple(w.items()), half, step)
obs = O.load_koeri(event_id=eid) if eid != "senaryo" else None
if obs is not None and len(obs):
    o, _ = run_scenario(ev, obs.lat.to_numpy(), obs.lon.to_numpy(), vs30=obs.vs30.to_numpy(), rupture=rup)
    o = add_uncertainty(o, tree, finite=rup.is_finite)
    obs = obs.reset_index(drop=True).assign(lt_p50=o.lt_p50, lt_p16=o.lt_p16, lt_p84=o.lt_p84)

c1, c2, c3 = st.columns(3)
c1.metric("Kaynak", "Sonlu fay" if rup.is_finite else "Nokta kaynak",
          f"L = {rup.length:.0f} km" if rup.is_finite else None)
c2.metric("Maks. medyan MMI", f"{to_roman(g.lt_p50.max())} ({g.lt_p50.max():.1f})")
c3.metric("MMI ≥ VII'ye maruz nüfus (medyan)",
          f"{table.loc[table.MMI.isin(['VII', 'VIII', 'IX', 'X+']), 'Medyan'].sum():,.0f}")

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
    st.write(f"Repi {d.repi:.1f} km · Rjb {d.rjb:.1f} km · Rrup {d.rrup:.1f} km")
    st.dataframe(pd.DataFrame([{"model": MODEL_LABELS[k], "medyan": d[k],
                                "σ": d.get(f"{k}_sd", np.nan)} for k in MODEL_LABELS]), hide_index=True)
    st.success(f"Mantık ağacı: {d.lt_p16:.2f} / {d.lt_p50:.2f} / {d.lt_p84:.2f} → {to_roman(d.lt_p50)} "
               f"({describe(d.lt_p50)[0]}) · P(≥VII) {d.p_ge_7:.0%} · P(≥VIII) {d.p_ge_8:.0%}")
with tab4:
    if obs is None or not len(obs):
        st.info("Bu senaryo için gözlem yok.")
    else:
        st.dataframe(obs[["station", "pgv_cms", "obs_mmi", "lt_p16", "lt_p50", "lt_p84"]], hide_index=True)
