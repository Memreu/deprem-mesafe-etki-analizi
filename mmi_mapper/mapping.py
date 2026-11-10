"""Folium harita çıktıları: basit senaryo haritası ve katmanlı şiddet haritası."""

from __future__ import annotations

import base64
import io

import folium
import numpy as np

from .scale import describe, to_roman

# ShakeMap MMI renk skalasına yakın tonlar (I → X)
MMI_COLORS = ["#ffffff", "#bfccff", "#a0e6ff", "#80ffff", "#7aff93", "#ffff00", "#ffc800", "#ff9100", "#ff0000",
              "#c80000"]


def _rupture_layer(rup, name="Fay (sonlu kaynak)"):
    fg = folium.FeatureGroup(name=name)
    if rup is not None and rup.is_finite:
        for ring in rup.outline_lonlat():
            folium.Polygon(ring, color="#7a0019", weight=1, fill=True, fill_opacity=0.15).add_to(fg)
        for seg in rup.trace_lonlat():
            folium.PolyLine([(la, lo) for lo, la in seg], color="#7a0019", weight=4,
                            tooltip=f"{rup.source} · L={rup.length:.0f} km").add_to(fg)
    return fg


def scenario_map(event, df, rup=None, model="allen2012_rrup") -> folium.Map:
    """Senaryo noktaları + fay + episantr."""
    m = folium.Map(location=[event.lat, event.lon], zoom_start=7, tiles="OpenStreetMap")
    folium.Marker([event.lat, event.lon], tooltip=f"Episantr · Mw {event.mag}",
                  icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    _rupture_layer(rup).add_to(m)
    fg = folium.FeatureGroup(name="Konumlar")
    col = "lt_p50" if "lt_p50" in df else model
    for i, r in df.reset_index(drop=True).iterrows():
        mmi = float(r[col])
        label, color = describe(mmi)
        rows = "".join(f"<tr><td>{k}</td><td>{r[k]:.2f}</td></tr>" for k in
                       ("allen2012_rrup", "bayrak2019", "kale2015_wgrw12", "lt_p16", "lt_p50", "lt_p84") if k in r)
        html = (f"<b>Konum {i + 1}</b><br>Repi {r.repi:.1f} km · Rrup {r.rrup:.1f} km · Vs30 {r.vs30:.0f}"
                f"<table>{rows}</table>")
        folium.CircleMarker([r.lat, r.lon], radius=8, color="#333", weight=1, fill=True, fill_color=color,
                            fill_opacity=0.9, popup=folium.Popup(html, max_width=280),
                            tooltip=f"Konum {i + 1}: MMI {to_roman(mmi)} ({label})").add_to(fg)
    fg.add_to(m)
    folium.LayerControl().add_to(m)
    return m


def _png_overlay(values2d, cmap, vmin, vmax, bounds, name, opacity=0.6, show=False):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rgba = cmap((np.clip(values2d, vmin, vmax) - vmin) / (vmax - vmin))
    rgba[np.isnan(values2d)] = 0
    buf = io.BytesIO()
    plt.imsave(buf, rgba[::-1], format="png")
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return folium.raster_layers.ImageOverlay(url, bounds=bounds, opacity=opacity, name=name, show=show,
                                             interactive=False, zindex=1)


def layered_map(event, grid_df, rup=None, observations=None, places=None) -> folium.Map:
    """Katmanlar: medyan, %16, %84, belirsizlik (σ), P(≥VII), P(≥VIII), fay, gözlemler, yerleşimler.

    ``grid_df``: ``grid.run_latlon_grid`` çıktısı (düzenli enlem/boylam ızgarası).
    """
    from matplotlib.colors import ListedColormap
    from matplotlib import colormaps

    ny, nx = grid_df.attrs["grid_shape"]
    lat = grid_df.lat.to_numpy().reshape(ny, nx)
    lon = grid_df.lon.to_numpy().reshape(ny, nx)
    dlat, dlon = lat[1, 0] - lat[0, 0], lon[0, 1] - lon[0, 0]
    bounds = [[lat.min() - dlat / 2, lon.min() - dlon / 2], [lat.max() + dlat / 2, lon.max() + dlon / 2]]
    mmi_cmap = ListedColormap(MMI_COLORS)

    m = folium.Map(location=[event.lat, event.lon], zoom_start=7, tiles="OpenStreetMap")
    layers = [("Medyan MMI (mantık ağacı)", "lt_p50", mmi_cmap, 0.5, 10.5, True),
              ("MMI %16", "lt_p16", mmi_cmap, 0.5, 10.5, False),
              ("MMI %84", "lt_p84", mmi_cmap, 0.5, 10.5, False),
              ("Belirsizlik σ (MMI)", "lt_sd", colormaps["viridis"], 0.6, 1.4, False),
              ("P(MMI ≥ VII)", "p_ge_7", colormaps["magma_r"], 0, 1, False),
              ("P(MMI ≥ VIII)", "p_ge_8", colormaps["magma_r"], 0, 1, False)]
    for name, col, cmap, vmin, vmax, show in layers:
        _png_overlay(grid_df[col].to_numpy().reshape(ny, nx), cmap, vmin, vmax, bounds, name, show=show).add_to(m)

    _rupture_layer(rup).add_to(m)
    folium.Marker([event.lat, event.lon], tooltip=f"Episantr · Mw {event.mag} · {event.event_id}",
                  icon=folium.Icon(color="red", icon="info-sign")).add_to(m)

    if observations is not None and len(observations):
        fg = folium.FeatureGroup(name="İstasyon / DYFI gözlemleri")
        for _, r in observations.iterrows():
            _, color = describe(r.obs_mmi)
            tip = f"{r.get('source', '')} {r.get('station', '')}: gözlem MMI {r.obs_mmi:.1f}"
            if "lt_p50" in r and np.isfinite(r.get("lt_p50", np.nan)):
                tip += f" · tahmin {r.lt_p50:.1f}"
            folium.RegularPolygonMarker([r.lat, r.lon], number_of_sides=3, radius=7, color="#000", weight=1,
                                        fill=True, fill_color=color, fill_opacity=1, tooltip=tip).add_to(fg)
        fg.add_to(m)

    if places is not None and len(places):
        fg = folium.FeatureGroup(name="Yerleşimler (nüfus)", show=False)
        for _, r in places.iterrows():
            folium.CircleMarker([r.lat, r.lon], radius=float(np.clip(np.sqrt(r.population) / 120, 2, 12)),
                                color="#222", weight=1, fill=True, fill_color=describe(r.lt_p50)[1], fill_opacity=0.9,
                                tooltip=f"{r['name']}: {int(r.population):,} kişi · MMI {r.lt_p16:.1f}/"
                                        f"{r.lt_p50:.1f}/{r.lt_p84:.1f} · P(≥VIII) {r.p_ge_8:.0%}").add_to(fg)
        fg.add_to(m)

    legend = "".join(f"<span style='background:{c};display:inline-block;width:18px;border:1px solid #999'>&nbsp;</span>"
                     f"<small>{to_roman(i + 1)}</small> " for i, c in enumerate(MMI_COLORS))
    m.get_root().html.add_child(folium.Element(
        "<div style='position:fixed;bottom:20px;left:20px;z-index:9999;background:white;padding:6px 8px;"
        f"border:1px solid #888;border-radius:4px;font-family:sans-serif'><b>MMI</b><br>{legend}</div>"))
    folium.LayerControl(collapsed=False).add_to(m)
    return m
