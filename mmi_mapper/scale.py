"""MMI ölçeği: Roma rakamı, Türkçe açıklama ve renk.

Açıklamalar USGS'in MMI ölçeği tanımlarındaki (Wood & Neumann 1931, USGS ShakeMap
lejantı) "Not felt / Weak / Light / Moderate / Strong / Very strong / Severe /
Violent / Extreme" sınıflarının Türkçe karşılıklarıdır.
"""

from __future__ import annotations

import math

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# (alt sınır, açıklama, harita rengi) — renkler ShakeMap lejantına yakın tonlardır
_CLASSES = [
    (1.0, "Hissedilmez", "#ffffff"),
    (1.5, "Zayıf", "#bfccff"),
    (3.5, "Hafif", "#a0e6ff"),
    (4.5, "Orta", "#80ffff"),
    (5.5, "Güçlü", "#7aff93"),
    (6.5, "Çok güçlü", "#ffff00"),
    (7.5, "Şiddetli", "#ffc800"),
    (8.5, "Yıkıcı", "#ff9100"),
    (9.5, "Aşırı", "#ff0000"),
]


def to_roman(mmi: float) -> str:
    """MMI değerini en yakın tam sayıya yuvarlayıp Roma rakamı döndürür."""
    if mmi is None or (isinstance(mmi, float) and math.isnan(mmi)):
        return "-"
    i = int(min(max(round(mmi), 1), 12))
    return ROMAN[i - 1]


def describe(mmi: float) -> tuple[str, str]:
    """(açıklama, renk) döndürür."""
    label, color = _CLASSES[0][1], _CLASSES[0][2]
    for lo, lab, col in _CLASSES:
        if mmi >= lo:
            label, color = lab, col
    return label, color
