"""Folium harita çıktıları."""

from __future__ import annotations

import folium

from .scale import describe, to_roman


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
    for i, r in df.reset_index(drop=True).iterrows():
        mmi = float(r[model])
        label, color = describe(mmi)
        rows = "".join(f"<tr><td>{k}</td><td>{r[k]:.2f}</td></tr>" for k in
                       ("allen2012_rrup", "bayrak2019", "kale2015_wgrw12") if k in r)
        html = (f"<b>Konum {i + 1}</b><br>Repi {r.repi:.1f} km · Rrup {r.rrup:.1f} km · Vs30 {r.vs30:.0f}"
                f"<table>{rows}</table>")
        folium.CircleMarker([r.lat, r.lon], radius=8, color="#333", weight=1, fill=True, fill_color=color,
                            fill_opacity=0.9, popup=folium.Popup(html, max_width=280),
                            tooltip=f"Konum {i + 1}: MMI {to_roman(mmi)} ({label})").add_to(fg)
    fg.add_to(m)
    folium.LayerControl().add_to(m)
    return m
