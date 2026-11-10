"""Model–gözlem karşılaştırması: artıklar, metrikler ve grafikler."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .model import MODEL_LABELS, Event, run_scenario
from .rupture import build_rupture
from .uncertainty import add_uncertainty

BENCH_MODELS = ["legacy", "allen2012_rhyp", "allen2012_rrup", "bayrak2019", "kale2015_wgrw12", "kale2015_ba14",
                "lt_mean"]
LABELS = {**MODEL_LABELS, "lt_mean": "Mantık ağacı (ortalama)"}
DIST_BINS = [0, 25, 50, 100, 200, 400, 1000]


def predict_for_observations(event: Event, obs: pd.DataFrame, rupture=None, rupture_geojson=None):
    """Gözlem noktalarında tüm modelleri çalıştırır ve artıkları (gözlem − tahmin) ekler."""
    rup = rupture or build_rupture(event.mag, event.lat, event.lon, event.depth, rake=event.rake,
                                   rupture_geojson=rupture_geojson)
    # Vs30 nokta bazında: gözlemde varsa o, yoksa raster / referans değer
    from .site import assign_vs30

    vs30, _ = assign_vs30(obs.lat.to_numpy(), obs.lon.to_numpy())
    if "vs30" in obs:
        given = obs["vs30"].to_numpy(float)
        vs30 = np.where(np.isfinite(given), given, vs30)
    pred, _ = run_scenario(event, obs.lat.to_numpy(), obs.lon.to_numpy(), vs30=vs30, rupture=rup)
    pred = add_uncertainty(pred, finite=rup.is_finite)
    keep = ["repi", "rhyp", "rjb", "rrup", "vs30"] + [c for c in pred.columns
                                                      if c in BENCH_MODELS or c.endswith("_sd") or c.startswith("lt_")
                                                      or c.startswith("p_ge")]
    out = pd.concat([obs.reset_index(drop=True).drop(columns=["vs30"], errors="ignore"),
                     pred[keep].reset_index(drop=True)], axis=1)
    for m in BENCH_MODELS:
        if m in out:
            out[f"res_{m}"] = out["obs_mmi"] - out[m]
    out["event_id"] = out.get("event_id", event.event_id)
    out["mag"] = event.mag
    out["finite_fault"] = rup.is_finite
    return out, rup


def metrics(res: pd.DataFrame, group: str | None = None) -> pd.DataFrame:
    """N, sapma (ortalama artık, gözlem − tahmin), RMSE, MAE, artık std."""
    rows = []
    groups = [("tümü", res)] if group is None else list(res.groupby(group, observed=True))
    for g, d in groups:
        for m in BENCH_MODELS:
            c = f"res_{m}"
            if c not in d:
                continue
            r = d[c].dropna()
            if r.empty:
                continue
            rows.append(dict(grup=g, model=LABELS[m], N=len(r), sapma=r.mean(), RMSE=np.sqrt((r**2).mean()),
                             MAE=r.abs().mean(), std=r.std(ddof=1) if len(r) > 1 else np.nan))
    return pd.DataFrame(rows)


def plot_residuals(res: pd.DataFrame, path: Path, title: str, models=("legacy", "allen2012_rrup", "kale2015_wgrw12",
                                                                         "lt_mean"), xcol="rrup", xlabel="Rrup (km)"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = [m for m in models if f"res_{m}" in res]
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.8), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, m in zip(axes, models):
        r = res[f"res_{m}"]
        for src, d in res.groupby("source"):
            ax.scatter(d[xcol], d[f"res_{m}"], s=14, alpha=0.6, label=src)
        x = res[xcol].to_numpy(float)
        if len(res) >= 10 and xcol in ("rrup", "rjb", "repi", "rhyp"):
            edges = np.array(DIST_BINS, float)
            idx = np.digitize(x, edges)
            cx, cy = [], []
            for k in np.unique(idx):
                sel = idx == k
                if sel.sum() >= 3:
                    cx.append(np.median(x[sel]))
                    cy.append(r[sel].mean())
            ax.plot(cx, cy, "k-o", ms=4, lw=1.5, label="bölme ortalaması")
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_title(f"{LABELS[m]}\nsapma {r.mean():+.2f} · RMSE {np.sqrt((r**2).mean()):.2f}", fontsize=9)
        if xcol in ("rrup", "rjb", "repi", "rhyp"):
            from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

            ax.set_xscale("log")
            ax.xaxis.set_major_locator(FixedLocator([1, 3, 10, 30, 100, 300, 1000]))
            ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel(xlabel)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Artık: gözlem − tahmin (MMI)")
    axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_obs_vs_pred(res: pd.DataFrame, path: Path, title: str, models=("legacy", "allen2012_rrup", "kale2015_wgrw12",
                                                                          "lt_mean")):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = [m for m in models if m in res]
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 4), sharex=True, sharey=True)
    for ax, m in zip(np.atleast_1d(axes), models):
        ax.scatter(res[m], res["obs_mmi"], s=14, alpha=0.6)
        lo, hi = 1, 10
        ax.plot([lo, hi], [lo, hi], "k--", lw=0.8)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_title(LABELS[m], fontsize=9)
        ax.set_xlabel("Tahmin (MMI)")
        ax.grid(alpha=0.3)
    np.atleast_1d(axes)[0].set_ylabel("Gözlem (MMI)")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
