"""Belirsizlik: çeyreklikler, aşma olasılıkları ve mantık ağacı.

Her model, bir noktadaki MMI'yı N(μ, σ) normal dağılımıyla tanımlar (IPE'lerde σ doğrudan
makaleden; GMPE+GMICE zincirinde σ² = (dMMI/dlnPGV·σ_lnPGV)² + σ_GMICE²).

Mantık ağacı, dalların ağırlıklı karışımıdır (epistemik + aleatorik belirsizlik):
    F(x) = Σ_i w_i · Φ((x − μ_i)/σ_i)
%16 / %50 / %84 değerleri bu karışımın ters dağılım fonksiyonundan sayısal olarak bulunur.
Aşma olasılığı literatür taramasındaki tanımla hesaplanır: P(MMI ≥ k) = Σ_i w_i·[1 − Φ((k − μ_i)/σ_i)].
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import norm

Q16, Q50, Q84 = 0.16, 0.50, 0.84


@dataclass
class LogicTree:
    """Model ağırlıkları. Toplamları 1'e normalize edilir.

    Varsayılan ağırlıkların gerekçesi (uzman yargısı; docs/logic_tree.md):
    * allen2012_rrup 0.30 — küresel, sonlu fay uzaklığı kullanan, yayımlanmış σ'sı olan IPE.
    * kale2015_wgrw12 0.30 — Türkiye GMPE'si + zemin (Vs30) + ShakeMap'in varsayılan GMICE'si.
    * kale2015_ba14 0.20 — Türkiye GMPE'si + Türkiye GMICE'si; σ_GMICE bir varsayım olduğu için daha düşük.
    * bayrak2019 0.20 — Türkiye IPE'si; ancak episantral uzaklık kullandığı için sonlu fay
      senaryolarında (Mw ≥ 6.5) ağırlığı 0.05'e indirilir ve fark diğer dallara orantılı dağıtılır.
    """

    weights: dict[str, float] = field(default_factory=lambda: {
        "allen2012_rrup": 0.30, "kale2015_wgrw12": 0.30, "kale2015_ba14": 0.20, "bayrak2019": 0.20})
    finite_fault_bayrak_weight: float = 0.05

    def effective(self, finite: bool) -> dict[str, float]:
        w = dict(self.weights)
        if finite and "bayrak2019" in w:
            w["bayrak2019"] = min(w["bayrak2019"], self.finite_fault_bayrak_weight)
        s = sum(w.values())
        return {k: v / s for k, v in w.items()}


def normal_quantiles(mu, sd, qs=(Q16, Q50, Q84)):
    mu, sd = np.asarray(mu, float), np.asarray(sd, float)
    return [mu + norm.ppf(q) * sd for q in qs]


def exceedance(mu, sd, level: float):
    return norm.sf((level - np.asarray(mu, float)) / np.asarray(sd, float))


def mixture_cdf(x, mus, sds, ws):
    return sum(w * norm.cdf((x - m) / s) for m, s, w in zip(mus, sds, ws))


def mixture_quantile(p: float, mus, sds, ws, tol=1e-4):
    """Karışım dağılımının p-çeyreği (vektörel ikiye bölme)."""
    lo = np.min([m - 6 * s for m, s in zip(mus, sds)], axis=0)
    hi = np.max([m + 6 * s for m, s in zip(mus, sds)], axis=0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        below = mixture_cdf(mid, mus, sds, ws) < p
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
        if np.max(hi - lo) < tol:
            break
    return 0.5 * (lo + hi)


def add_uncertainty(df: pd.DataFrame, tree: LogicTree | None = None, finite: bool = False,
                    levels=(7, 8)) -> pd.DataFrame:
    """Model sütunlarından mantık ağacı ve model bazında çeyreklik/aşma sütunları üretir.

    Eklenen sütunlar: ``<model>_p16/_p84``, ``lt_mean``, ``lt_sd``, ``lt_p16``, ``lt_p50``, ``lt_p84``,
    ``p_ge_7``, ``p_ge_8`` (mantık ağacı).
    """
    tree = tree or LogicTree()
    w = {k: v for k, v in tree.effective(finite).items() if k in df}
    s = sum(w.values())
    w = {k: v / s for k, v in w.items()}
    out = df.copy()
    for k in w:
        p16, p84 = normal_quantiles(df[k], df[f"{k}_sd"], (Q16, Q84))
        out[f"{k}_p16"], out[f"{k}_p84"] = p16, p84
    mus = [df[k].to_numpy(float) for k in w]
    sds = [df[f"{k}_sd"].to_numpy(float) for k in w]
    ws = list(w.values())
    mean = sum(wi * m for wi, m in zip(ws, mus))
    var = sum(wi * (s_**2 + (m - mean) ** 2) for wi, m, s_ in zip(ws, mus, sds))
    out["lt_mean"], out["lt_sd"] = mean, np.sqrt(var)
    for q, name in ((Q16, "lt_p16"), (Q50, "lt_p50"), (Q84, "lt_p84")):
        out[name] = mixture_quantile(q, mus, sds, ws)
    for lev in levels:
        out[f"p_ge_{lev}"] = sum(wi * exceedance(m, s_, lev) for wi, m, s_ in zip(ws, mus, sds))
    out.attrs.update(df.attrs)
    out.attrs["logic_tree_weights"] = w
    return out
