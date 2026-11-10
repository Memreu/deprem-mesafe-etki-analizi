"""Yer hareketi → şiddet dönüşüm denklemleri (GMICE), PGV tabanlı.

Kaynaklar
---------
* Worden, C.B., Gerstenberger, M.C., Rhoades, D.A., Wald, D.J. (2012). Probabilistic
  relationships between ground-motion parameters and MMI in California.
  BSSA 102(1), 204–221. doi:10.1785/0120110156
  Katsayılar: USGS ``esi-shakelib`` 1.2.1, ``esi_shakelib/gmice/wgrw12.py`` (WGRW12 sınıfı,
  PGV için ``_constants`` ve ``_constants2`` tabloları).
* Bilal, M., Askan, A. (2014). Relationships between felt intensity and recorded
  ground-motion parameters for Turkey. BSSA 104(1), 484–496. doi:10.1785/0120130093
  Denklem (makale özeti): MMI = 2.673 + 4.340·log10(PGV), PGV cm/s.

Bileşen notu: Kale vd. (2015) geometrik ortalama PGV verir. WGRW12 ve Bilal & Askan
kayıtların yatay bileşenleriyle türetilmiştir. Bileşen dönüşümü (ör. geometrik ortalama
→ büyük bileşen) burada uygulanmaz; bu, yaklaşık %10–20'lik bir PGV farkına,
yani ~0,1–0,3 MMI'lık sistematik bir sapmaya yol açabilir.
"""

from __future__ import annotations

import numpy as np

LOG10E = np.log10(np.e)

# esi-shakelib WGRW12, PGV satırları
WGRW12_PGV = dict(C1=3.78, C2=1.47, C3=2.89, C4=3.16, C5=0.90, C6=0.00, C7=-0.18, T1=0.53, T2=4.56,
                  SMMI=0.63, SPGM=0.38)
WGRW12_PGV_LOW = dict(C1=4.62, C2=2.17, T1=-1.21, T2=2.0)

BILAL_ASKAN2014_PGV = dict(a=2.673, b=4.340)
# VARSAYIM: Bilal & Askan (2014) PGV denkleminin standart sapmasına birincil kaynaktan
# erişilemedi. Belirsizlik zincirinde WGRW12'nin PGV σ_MMI değeri (0.63) vekil olarak kullanılır.
BILAL_ASKAN2014_SIGMA_ASSUMED = 0.63


def wgrw12_pgv(pgv_cms, rrup_km=None, mag=None):
    """Worden vd. (2012) PGV→MMI. (MMI, dMMI/dlnPGV, σ_GMICE) döndürür.

    ``rrup_km`` ve ``mag`` verilirse makaledeki uzaklık/büyüklük düzeltme terimi
    (C5 + C6·log10 R + C7·M; R 10–300 km'ye, M 3.0–7.3'e kırpılır) eklenir.
    """
    c, c2 = WGRW12_PGV, WGRW12_PGV_LOW
    pgv = np.asarray(pgv_cms, dtype=float)
    lp = np.log10(np.maximum(pgv, 1e-12))
    mmi = np.where(lp < c2["T1"], c2["C1"] + c2["C2"] * lp,
                   np.where(lp < c["T1"], c["C1"] + c["C2"] * lp, c["C3"] + c["C4"] * lp))
    slope = np.where(lp < c2["T1"], c2["C2"], np.where(lp < c["T1"], c["C2"], c["C4"])) * LOG10E
    if rrup_km is not None and mag is not None:
        ldd = np.log10(np.clip(np.asarray(rrup_km, float), 10, 300))
        mmi = mmi + c["C5"] + c["C6"] * ldd + c["C7"] * np.clip(mag, 3.0, 7.3)
    mmi = np.clip(mmi, 1.0, 10.0)
    return mmi, slope, np.full_like(mmi, c["SMMI"])


def bilal_askan2014_pgv(pgv_cms):
    """Bilal & Askan (2014) Türkiye PGV→MMI. (MMI, dMMI/dlnPGV, σ_GMICE[varsayım]) döndürür."""
    k = BILAL_ASKAN2014_PGV
    pgv = np.asarray(pgv_cms, dtype=float)
    mmi = np.clip(k["a"] + k["b"] * np.log10(np.maximum(pgv, 1e-12)), 1.0, 10.0)
    slope = np.full_like(mmi, k["b"] * LOG10E)
    return mmi, slope, np.full_like(mmi, BILAL_ASKAN2014_SIGMA_ASSUMED)


GMICES = {"wgrw12": wgrw12_pgv, "ba14": bilal_askan2014_pgv}


def chain_sigma(slope, sigma_ln_pgv, sigma_gmice):
    """GMPE ve GMICE belirsizliklerinin birleşimi (birinci derece yaklaşım).

    σ_MMI² = (dMMI/dlnPGV · σ_lnPGV)² + σ_GMICE²
    """
    return np.sqrt((slope * sigma_ln_pgv) ** 2 + sigma_gmice**2)
