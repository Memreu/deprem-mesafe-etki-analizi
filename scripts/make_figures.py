"""README görsellerini ve Kahramanmaraş senaryo çıktılarını üretir.

    python scripts/make_figures.py

Çıktılar: images/*.png, results/kahramanmaras_exposure.csv, results/kahramanmaras_places.csv,
results/kahramanmaras_map.html (katmanlı folium haritası)
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mmi_mapper import observations as O  # noqa: E402
from mmi_mapper.exposure import exposure  # noqa: E402
from mmi_mapper.grid import run_latlon_grid  # noqa: E402
from mmi_mapper.mapping import MMI_COLORS, layered_map  # noqa: E402
from mmi_mapper.model import Event  # noqa: E402

warnings.filterwarnings("ignore")
IMG = ROOT / "images"
RES = ROOT / "results"


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    IMG.mkdir(exist_ok=True)
    ev = Event(7.8, 37.2256, 37.0143, 10.0, event_id="us6000jllz")
    g, rup = run_latlon_grid(ev, 2.5, 0.05)
    table, places, _ = exposure(ev, 3.0, rupture=rup)
    table.to_csv(RES / "kahramanmaras_exposure.csv", index=False, float_format="%.0f")
    places.to_csv(RES / "kahramanmaras_places.csv", index=False, float_format="%.3f")
    import pandas as pd

    usgs = pd.read_csv(ROOT / "data" / "observations" / "usgs_observations.csv")
    afad = usgs[(usgs.event_id == "us6000jllz") & (usgs.source == "AFAD (ShakeMap)")]
    obs = pd.concat([O.load_koeri(event_id="us6000jllz"), afad], ignore_index=True)
    layered_map(ev, g, rup, obs, places).save(RES / "kahramanmaras_map.html")

    ny, nx = g.attrs["grid_shape"]
    LAT, LON = g.lat.to_numpy().reshape(ny, nx), g.lon.to_numpy().reshape(ny, nx)
    cmap = ListedColormap(MMI_COLORS)
    norm = BoundaryNorm(np.arange(0.5, 11.0, 1.0), cmap.N)
    panels = [("legacy", "Eski formül (doğrulanmamış, nokta kaynak)", cmap, norm),
              ("lt_p50", "Mantık ağacı medyanı (sonlu fay, Vs30 = 760 m/s)", cmap, norm),
              ("p_ge_8", "P(MMI ≥ VIII)", plt.get_cmap("magma_r"), None)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    top = places.nlargest(8, "population")
    for ax, (col, title, cm, nm) in zip(axes, panels):
        im = ax.pcolormesh(LON, LAT, g[col].to_numpy().reshape(ny, nx), cmap=cm, norm=nm,
                           vmin=None if nm else 0, vmax=None if nm else 1, shading="nearest")
        for seg in rup.trace_lonlat():
            xs, ys = zip(*seg)
            ax.plot(xs, ys, color="k", lw=2.2)
        ax.plot(ev.lon, ev.lat, marker="*", ms=14, color="k", mec="w")
        ax.scatter(obs.lon, obs.lat, marker="^", s=14, c="w", edgecolors="k", linewidths=0.6, zorder=5)
        for _, r in top.iterrows():
            ax.plot(r.lon, r.lat, "o", ms=3, color="k")
            ax.annotate(r["name"], (r.lon, r.lat), fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_title(title, fontsize=10)
        ax.set_aspect(1 / np.cos(np.radians(ev.lat)))
        ax.set_xlabel("Boylam")
        cb = fig.colorbar(im, ax=ax, shrink=0.85)
        if nm is not None:
            cb.set_ticks(range(1, 11))
            cb.set_ticklabels(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"])
    axes[0].set_ylabel("Enlem")
    fig.suptitle("Kahramanmaraş (Pazarcık) Mw 7.8 — 6 Şubat 2023 · siyah çizgi: GEM izi + Thingbaijam (2017) fayı, "
                 "üçgen: KOERI ve AFAD istasyonları", fontsize=11)
    fig.savefig(IMG / "kahramanmaras_mmi_map.png", dpi=130)
    plt.close(fig)

    # Uzaklıkla azalım: dört model, Mw 7.8 nokta kaynak vs. sonlu fay
    from mmi_mapper import ipe

    r = np.logspace(0, np.log10(400), 200)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for mw, ls in ((6.0, "--"), (7.0, "-.")) :
        ax.plot(r, ipe.legacy_unverified(mw, r, 10)[0], color="#c0392b", ls=ls, lw=1.4, label=f"Eski formül Mw {mw}")
        ax.plot(r, ipe.allen2012_rhyp(mw, np.hypot(r, 10))[0], color="#2c7fb8", ls=ls, lw=1.4,
                label=f"Allen 2012 Rhyp Mw {mw}")
        ax.plot(r, ipe.bayrak2019(mw, r, 10, "R3")[0], color="#31a354", ls=ls, lw=1.4, label=f"Bayrak 2019 R3 Mw {mw}")
    ax.axvspan(100, 300, color="0.9", zorder=0)
    ax.text(110, 8.9, "100–300 km: eski formül\n+1,6…+2,2 MMI fazla", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("Episantral uzaklık (km), derinlik 10 km")
    ax.set_ylabel("MMI")
    ax.set_ylim(1, 10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(IMG / "attenuation_comparison.png", dpi=150)
    plt.close(fig)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
