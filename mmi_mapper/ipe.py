"""Şiddet tahmin denklemleri (Intensity Prediction Equations, IPE).

Her model, (medyan MMI, toplam sigma) çifti döndürür. Katsayılar hafızadan değil,
aşağıda belirtilen birincil kaynaklardan alınmıştır; testler OpenQuake
uygulamasıyla birebir eşleşmeyi doğrular (tests/test_ipe.py).

Kaynaklar
---------
* Allen, T.I., Wald, D.J., Worden, C.B. (2012). Intensity attenuation for active
  crustal regions. J. Seismology 16, 409–433. doi:10.1007/s10950-012-9278-7
  Katsayılar: OpenQuake hazardlib ``gsim/allen_2012_ipe.py``
  (``AllenEtAl2012`` ve ``AllenEtAl2012Rhypo`` sınıfları, oq-engine 3.26).
* Bayrak, E., Nas, M., Bayrak, Y. (2019). New macroseismic intensity predictive
  models for Turkey. Acta Geophysica 67(6), 1483–1513.
  doi:10.1007/s11600-019-00357-4 — Tablo 4 (WLS katsayıları ve σY).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Allen, Wald & Worden (2012)
# ---------------------------------------------------------------------------
# OpenQuake: AllenEtAl2012.COEFFS (Rrup sürümü)
ALLEN2012_RRUP = dict(c0=3.950, c1=0.913, c2=-1.107, c3=0.813, s1=0.72, s2=0.23, s3=44.7)
# OpenQuake: AllenEtAl2012Rhypo.COEFFS (Rhyp sürümü)
ALLEN2012_RHYP = dict(
    c0=2.085, c1=1.428, c2=-1.402, c4=0.078, m1=-0.209, m2=2.042, s1=0.82, s2=0.37, s3=22.9
)


def allen2012_rrup(mw: float, rrup_km) -> tuple[np.ndarray, np.ndarray]:
    """Allen vd. (2012) — en yakın fay uzaklığı (Rrup) sürümü.

    MMI = c0 + c1·M + c2·ln( sqrt(Rrup² + (1 + c3·exp(M−5))²) )
    σ(R) = s1 + s2 / (1 + (Rrup/s3)²)
    """
    c = ALLEN2012_RRUP
    r = np.asarray(rrup_km, dtype=float)
    mean = c["c0"] + c["c1"] * mw + c["c2"] * np.log(np.sqrt(r**2 + (1.0 + c["c3"] * np.exp(mw - 5.0)) ** 2))
    sigma = c["s1"] + c["s2"] / (1.0 + (r / c["s3"]) ** 2)
    return mean, sigma


def allen2012_rhyp(mw: float, rhyp_km) -> tuple[np.ndarray, np.ndarray]:
    """Allen vd. (2012) — hiposantral uzaklık (Rhyp) sürümü (nokta kaynak).

    Rm = m1 + m2·exp(M−5)
    MMI = c0 + c1·M + c2·ln( sqrt(Rhyp² + Rm²) ) + S,  S = c4·ln(Rhyp/50) (Rhyp > 50 km), aksi 0
    σ(R) = s1 + s2 / (1 + (Rhyp/s3)²)
    """
    c = ALLEN2012_RHYP
    r = np.asarray(rhyp_km, dtype=float)
    rm = c["m1"] + c["m2"] * np.exp(mw - 5.0)
    mean = c["c0"] + c["c1"] * mw + c["c2"] * np.log(np.sqrt(r**2 + rm**2))
    mean = mean + np.where(r > 50.0, c["c4"] * np.log(np.maximum(r, 50.0) / 50.0), 0.0)
    sigma = c["s1"] + c["s2"] / (1.0 + (r / c["s3"]) ** 2)
    return mean, sigma


# ---------------------------------------------------------------------------
# Bayrak, Nas & Bayrak (2019) — Türkiye
# ---------------------------------------------------------------------------
# Tablo 4 (WLS): a, b, c, d ve σY. Uzaklık: episantral (Repi, km); h: odak derinliği (km).
# Geçerlilik (makale): 4.5 ≤ Mw ≤ 7.9, 3 ≤ h ≤ 80 km, 4 ≤ MMI ≤ 11.
# NOT (log tabanı): Makale "log" yazar ama tabanı açıkça belirtmez. Model biçimleri
# Bakun & Wentworth (1997) ve Dowrick & Rhoades (2005) gibi log10 kullanan
# çalışmalardan alındığı için burada log10 varsayılmıştır. σY sütunu makalede
# ayrıca tanımlanmamıştır; toplam standart sapma olarak yorumlanmıştır.
BAYRAK2019 = {
    "R1": dict(a=7.023, b=0.703, c=-2.826, d=None, sigma=1.292),
    "R2": dict(a=5.002, b=0.750, c=-0.0094, d=-1.454, sigma=1.311),
    "R3": dict(a=7.494, b=0.744, c=-3.377, d=0.017, sigma=1.270),
    "R4": dict(a=2.281, b=0.874, c=-0.618, d=-0.016, sigma=1.264),
}
BAYRAK2019_VALID = dict(mw=(4.5, 7.9), depth=(3.0, 80.0))


def bayrak2019(mw: float, repi_km, depth_km: float, model: str = "R3") -> tuple[np.ndarray, np.ndarray]:
    """Bayrak vd. (2019) Türkiye IPE'si (R1–R4).

    R1: I = a + b·Mw + c·log(Repi)                                   (Bakun & Wentworth 1997 biçimi)
    R2: I = a + b·Mw + c·Repi + d·log(Repi)                          (Bakun vd. 2003 biçimi)
    R3: I = a + b·Mw + c·log( (Repi³ + h³)^(1/3) ) + d·h             (Dowrick & Rhoades 2005 biçimi)
    R4: I = a + b·Mw + c·log(1 + Repi²/h²) + d·( sqrt(Repi² + h²) − h ) (Sørensen vd. 2009 biçimi)
    """
    if model not in BAYRAK2019:
        raise ValueError(f"Bilinmeyen Bayrak 2019 modeli: {model}")
    k = BAYRAK2019[model]
    r = np.maximum(np.asarray(repi_km, dtype=float), 1.0)  # log(0)'dan kaçın
    h = float(depth_km)
    lo, hi = BAYRAK2019_VALID["mw"]
    if not lo <= mw <= hi:
        warnings.warn(f"Bayrak 2019: Mw={mw} geçerlilik aralığı dışında ({lo}–{hi}).", stacklevel=2)
    if model == "R1":
        mean = k["a"] + k["b"] * mw + k["c"] * np.log10(r)
    elif model == "R2":
        mean = k["a"] + k["b"] * mw + k["c"] * r + k["d"] * np.log10(r)
    elif model == "R3":
        mean = k["a"] + k["b"] * mw + k["c"] * np.log10(np.cbrt(r**3 + h**3)) + k["d"] * h
    else:
        h = max(h, 1.0)
        mean = k["a"] + k["b"] * mw + k["c"] * np.log10(1.0 + r**2 / h**2) + k["d"] * (np.sqrt(r**2 + h**2) - h)
    return mean, np.full_like(mean, k["sigma"], dtype=float)


# ---------------------------------------------------------------------------
# Eski (kaynağı doğrulanamayan) formül — yalnızca karşılaştırma için
# ---------------------------------------------------------------------------
def legacy_unverified(mw: float, repi_km, depth_km: float) -> tuple[np.ndarray, np.ndarray]:
    """DOĞRULANMAMIŞ: projenin ilk sürümündeki formül.

    MMI = 1.62 + 1.22·Mw − 0.00255·R − 1.29·log10(R),  R = sqrt(Repi² + h²)

    Yayımlanmış bir kaynağı bulunamamıştır. Allen vd. (2012)'ye göre 100–300 km
    aralığında şiddeti ~1,5–2 MMI fazla tahmin eder. Yalnızca benchmark'ta
    "önceki sürüm" referansı olarak tutulur; operasyonel kullanım için değildir.
    Belirsizlik bilinmediğinden sigma NaN döner.
    """
    r = np.maximum(np.sqrt(np.asarray(repi_km, dtype=float) ** 2 + depth_km**2), 1.0)
    mean = 1.62 + 1.22 * mw - 0.00255 * r - 1.29 * np.log10(r)
    return mean, np.full_like(mean, np.nan, dtype=float)


@dataclass(frozen=True)
class IPEInfo:
    key: str
    name: str
    distance: str
    reference: str


IPE_REGISTRY = {
    "allen2012_rrup": IPEInfo("allen2012_rrup", "Allen vd. 2012 (Rrup)", "rrup", "doi:10.1007/s10950-012-9278-7"),
    "allen2012_rhyp": IPEInfo("allen2012_rhyp", "Allen vd. 2012 (Rhyp)", "rhyp", "doi:10.1007/s10950-012-9278-7"),
    "bayrak2019": IPEInfo("bayrak2019", "Bayrak vd. 2019 (R3, Türkiye)", "repi", "doi:10.1007/s11600-019-00357-4"),
    "legacy": IPEInfo("legacy", "Eski formül (doğrulanmamış)", "rhyp", "kaynak yok"),
}
