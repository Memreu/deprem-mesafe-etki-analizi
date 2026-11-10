"""Folium harita çıktıları."""

from __future__ import annotations

import folium

from .scale import describe, to_roman


def simple_map(eq_lat: float, eq_lon: float, table: dict) -> folium.Map:
    """Nokta kaynak sonuçları için basit harita (deprem + konumlar)."""
    m = folium.Map(location=[eq_lat, eq_lon], zoom_start=7, tiles="OpenStreetMap")
    folium.Marker([eq_lat, eq_lon], tooltip="Episantr", icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    for i, (la, lo) in enumerate(zip(table["lat"], table["lon"]), 1):
        mmi = float(table["allen"][i - 1])
        label, color = describe(mmi)
        html = (f"<b>Konum {i}</b><br>Repi: {table['repi'][i-1]:.1f} km<br>"
                f"Allen 2012: {mmi:.2f} ({to_roman(mmi)}, {label})<br>"
                f"Bayrak 2019: {table['bayrak'][i-1]:.2f}")
        folium.CircleMarker([la, lo], radius=8, color="#333", weight=1, fill=True, fill_color=color,
                            fill_opacity=0.9, popup=folium.Popup(html, max_width=260),
                            tooltip=f"Konum {i}: MMI {to_roman(mmi)}").add_to(m)
        folium.PolyLine([(eq_lat, eq_lon), (la, lo)], color="orange", weight=2,
                        tooltip=f"{table['repi'][i-1]:.1f} km").add_to(m)
    return m
