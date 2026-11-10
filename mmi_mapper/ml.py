"""Aşama 4 — fiziksel omurga + öğrenilen artık (hibrit model).

    MMI_tahmin = MMI_fizik(Mw, Rrup, Vs30) + f_LightGBM(özellikler)

* Omurga: Kale 2015 → WGRW12 (benchmark'ta Mw ≥ 6 kümesinde en düşük RMSE).
* LightGBM, gözlemi ``init_score = omurga`` ile öğrenir; yani yalnızca artığı modeller.
* Monotonluk kısıtları: Mw ↑ (+1), log10 Rrup ↓ (−1), log10 Vs30 ↓ (−1). Omurga da bu yönlerde monoton
  olduğu için toplam tahmin fiziksel olarak tutarlı kalır (uzaklık arttıkça şiddet artmaz).
* Doğrulama: deprem bazında gruplandırılmış çapraz doğrulama (GroupKFold; grup = kayıt penceresi
  örtüşen depremleri birleştiren ``window_group``), veri sızıntısını önler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ["mag", "log_rrup", "log_vs30", "ev_depth_km", "lat", "lon"]
MONOTONE = [1, -1, -1, 0, 0, 0]
BACKBONE = "kale2015_wgrw12"
PARAMS = dict(objective="regression", learning_rate=0.03, n_estimators=300, num_leaves=8, max_depth=3,
              min_child_samples=25, subsample=0.8, subsample_freq=1, colsample_bytree=0.9, reg_lambda=5.0,
              monotone_constraints=MONOTONE, monotone_constraints_method="advanced", random_state=42, verbose=-1)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    X["mag"] = df["mag"].astype(float)
    X["log_rrup"] = np.log10(np.maximum(df["rrup"].astype(float), 1.0))
    X["log_vs30"] = np.log10(df["vs30"].astype(float))
    X["ev_depth_km"] = df["ev_depth_km"].astype(float)
    X["lat"] = df["lat"].astype(float)
    X["lon"] = df["lon"].astype(float)
    return X[FEATURES]


@dataclass
class ResidualModel:
    backbone: str = BACKBONE
    params: dict = field(default_factory=lambda: dict(PARAMS))
    model: object = None

    def fit(self, df: pd.DataFrame):
        import lightgbm as lgb

        self.model = lgb.LGBMRegressor(**self.params)
        self.model.fit(build_features(df), df["obs_mmi"].to_numpy(float), init_score=df[self.backbone].to_numpy(float))
        return self

    def correction(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(build_features(df))  # init_score dahil değil → yalnızca artık düzeltmesi

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return df[self.backbone].to_numpy(float) + self.correction(df)

    def save(self, path):
        self.model.booster_.save_model(str(path))

    @classmethod
    def load(cls, path):
        import lightgbm as lgb

        m = cls()
        m.model = lgb.Booster(model_file=str(path))
        return m


def rmse(r):
    r = np.asarray(r, float)
    return float(np.sqrt(np.mean(r**2)))


def grouped_cv(df: pd.DataFrame, n_splits=5, group_col="window_group", backbone=BACKBONE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Katman dışı (out-of-fold) tahminler ve kat bazında metrikler.

    Karşılaştırılan yöntemler: omurga; omurga + eğitim katının ortalama artığı (sabit kaydırma);
    omurga + LightGBM.
    """
    from sklearn.model_selection import GroupKFold

    oof = df[["event_id", group_col, "mag", "rrup", "obs_mmi", backbone]].copy()
    oof["shift"] = np.nan
    oof["hybrid"] = np.nan
    rows = []
    for k, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(df, groups=df[group_col])):
        dtr, dte = df.iloc[tr], df.iloc[te]
        bias = float((dtr.obs_mmi - dtr[backbone]).mean())
        m = ResidualModel(backbone=backbone).fit(dtr)
        oof.iloc[te, oof.columns.get_loc("shift")] = dte[backbone].to_numpy() + bias
        oof.iloc[te, oof.columns.get_loc("hybrid")] = m.predict(dte)
        for name, col in (("omurga", backbone), ("omurga + sabit kaydırma", "shift"), ("omurga + LightGBM", "hybrid")):
            rows.append(dict(kat=k + 1, yöntem=name, N=len(te), deprem=dte.event_id.nunique(),
                             RMSE=rmse(dte.obs_mmi - oof.iloc[te][col]), sapma=float((dte.obs_mmi - oof.iloc[te][col]).mean())))
    return oof, pd.DataFrame(rows)


def check_monotonic(model: ResidualModel, df: pd.DataFrame, n=200, seed=0) -> dict[str, bool]:
    """Kısıtların sağlandığını rastgele örneklerde sınar (artık bileşen için)."""
    base = df.sample(min(n, len(df)), random_state=seed)
    out = {}
    for feat, sign, col, step in (("mag", 1, "mag", 0.5), ("log_rrup", -1, "rrup", None), ("log_vs30", -1, "vs30", None)):
        lo, hi = base.copy(), base.copy()
        if col == "rrup":
            hi[col] = lo[col] * 2.0
        elif col == "vs30":
            hi[col] = lo[col] * 1.5
        else:
            hi[col] = lo[col] + step
        d = model.correction(hi) - model.correction(lo)
        out[feat] = bool(np.all(sign * d >= -1e-9))
    return out
