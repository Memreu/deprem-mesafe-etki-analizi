"""OpenQuake hazardlib üzerinden yer hareketi tahmini (GMPE).

Varsayılan model: Kale, Akkar, Ansari & Hamzehloo (2015), Türkiye ve İran için
bölgesel GMPE — OpenQuake ``KaleEtAl2015Turkey`` sınıfı (Mw, Rjb, Vs30, rake).
"""

from __future__ import annotations

import numpy as np


def _ctx(mag, rake, rjb, vs30, rrup=None, rhypo=None, ztor=0.0, hypo_depth=10.0, dip=90.0, width=10.0):
    from openquake.hazardlib.contexts import RuptureContext

    n = len(rjb)
    ctx = RuptureContext()
    ctx.mag = float(mag)
    ctx.rake = float(rake)
    ctx.ztor = float(ztor)
    ctx.hypo_depth = float(hypo_depth)
    ctx.dip = float(dip)
    ctx.width = float(width)
    ctx.rjb = np.asarray(rjb, float)
    ctx.rrup = np.asarray(rrup if rrup is not None else rjb, float)
    ctx.rhypo = np.asarray(rhypo if rhypo is not None else ctx.rrup, float)
    ctx.vs30 = np.broadcast_to(np.asarray(vs30, float), (n,)).copy()
    ctx.sids = np.arange(n)
    return ctx


def predict(gsim_name: str, imt: str, mag, rake, rjb, vs30, **kw):
    """Herhangi bir OpenQuake GSIM'i için (ln medyan, σ_toplam, τ, φ) döndürür."""
    from openquake.hazardlib import valid
    from openquake.hazardlib.contexts import get_mean_stds
    from openquake.hazardlib.imt import from_string

    gsim = valid.gsim(gsim_name)
    ms = get_mean_stds(gsim, _ctx(mag, rake, rjb, vs30, **kw), [from_string(imt)])
    mean, sig, tau, phi = (ms[i][0] for i in range(4))
    return mean, sig, tau, phi


def kale2015_pgv(mag, rake, rjb, vs30):
    """Kale vd. (2015) Türkiye: ln PGV (cm/s) medyanı ve σ_lnPGV."""
    mean, sig, _, _ = predict("KaleEtAl2015Turkey", "PGV", mag, rake, rjb, vs30)
    return mean, sig
