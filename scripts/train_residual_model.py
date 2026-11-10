"""Aşama 4 — LightGBM artık modeli, gruplandırılmış çapraz doğrulama ve SHAP.

    python scripts/run_benchmark.py        # önce artık tablosunu üretir
    python scripts/train_residual_model.py

Çıktılar: results/ml/
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mmi_mapper import ml  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "results" / "ml"


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ROOT / "results" / "residuals_koeri_all.csv")
    df = df.dropna(subset=["obs_mmi", ml.BACKBONE, "vs30", "rrup"]).reset_index(drop=True)
    df["window_group"] = df["window_group"].fillna(df["event_id"])

    oof, folds = ml.grouped_cv(df)
    folds.to_csv(OUT / "cv_folds.csv", index=False, float_format="%.3f")
    summary = []
    for subset, sel in (("tümü", np.ones(len(oof), bool)), ("Mw ≥ 6", oof.mag >= 6.0), ("Rrup ≤ 50 km", oof.rrup <= 50)):
        d = oof[sel]
        for name, col in (("omurga (Kale 2015 → WGRW12)", ml.BACKBONE), ("omurga + sabit kaydırma", "shift"),
                          ("omurga + LightGBM", "hybrid")):
            r = d.obs_mmi - d[col]
            summary.append(dict(küme=subset, yöntem=name, N=len(d), deprem=d.event_id.nunique(),
                                sapma=float(r.mean()), RMSE=ml.rmse(r)))
    # İstasyon dışarıda bırakılarak: lat/lon istasyon terimi gibi davranıyorsa yeni istasyonlara genellemez
    oof_st, _ = ml.grouped_cv(df, group_col="station")
    for name, col in (("omurga (Kale 2015 → WGRW12)", ml.BACKBONE), ("omurga + sabit kaydırma", "shift"),
                      ("omurga + LightGBM", "hybrid")):
        r = oof_st.obs_mmi - oof_st[col]
        summary.append(dict(küme="tümü · istasyon bazlı CV", yöntem=name, N=len(oof_st), deprem=oof_st.event_id.nunique(),
                            sapma=float(r.mean()), RMSE=ml.rmse(r)))
    summary = pd.DataFrame(summary)
    summary.to_csv(OUT / "cv_summary.csv", index=False, float_format="%.3f")
    oof.to_csv(OUT / "oof_predictions.csv", index=False, float_format="%.4f")

    final = ml.ResidualModel().fit(df)
    final.save(OUT / "lgbm_residual_model.txt")
    mono = ml.check_monotonic(final, df)

    X = ml.build_features(df)
    sv = shap.TreeExplainer(final.model).shap_values(X)
    imp = pd.DataFrame({"özellik": ml.FEATURES, "ortalama |SHAP|": np.abs(sv).mean(axis=0)}).sort_values(
        "ortalama |SHAP|", ascending=False)
    imp.to_csv(OUT / "shap_importance.csv", index=False, float_format="%.4f")
    plt.figure()
    shap.summary_plot(sv, X, show=False, plot_size=(7, 4))
    plt.title("SHAP — artık düzeltmesine katkı (MMI)", fontsize=10)
    plt.tight_layout()
    plt.savefig(OUT / "shap_summary.png", dpi=150)
    plt.close("all")

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, (col, lab) in zip(axes, ((ml.BACKBONE, "Omurga"), ("hybrid", "Omurga + LightGBM (katman dışı)"))):
        r = oof.obs_mmi - oof[col]
        ax.scatter(oof.rrup, r, s=6, alpha=0.4)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlabel("Rrup (km)")
        ax.set_title(f"{lab}\nsapma {r.mean():+.2f} · RMSE {ml.rmse(r):.2f}", fontsize=9)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Artık (MMI)")
    fig.tight_layout()
    fig.savefig(OUT / "oof_residuals.png", dpi=150)
    plt.close(fig)

    meta = dict(backbone=ml.BACKBONE, features=ml.FEATURES, monotone=ml.MONOTONE, params={k: v for k, v in ml.PARAMS.items()
                                                                                           if k != "monotone_constraints"},
                n_records=len(df), n_events=int(df.event_id.nunique()), n_groups=int(df.window_group.nunique()),
                monotonic_check=mono)
    (OUT / "model_card.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(summary.to_string(index=False))
    print(imp.to_string(index=False))
    print("monotonluk:", mono)


if __name__ == "__main__":
    main()
