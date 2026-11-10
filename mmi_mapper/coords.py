"""Koordinat ayrıştırma ve uzaklık yardımcıları."""

from __future__ import annotations

import re

import numpy as np

_DMS = re.compile(r"^\s*(\d+)°\s*(\d+)'\s*([\d.]+)\"?\s*([NSEW])\s*$", re.IGNORECASE)

EARTH_RADIUS_KM = 6371.0088  # IUGG ortalama yarıçap


def dms_to_decimal(koordinat: str) -> float:
    """DMS (39°55'29.1\"N) biçimini ondalık dereceye çevirir."""
    eslesen = _DMS.match(koordinat)
    if not eslesen:
        raise ValueError(f"Koordinat formatı hatalı: {koordinat!r}")
    derece, dakika, saniye, yon = eslesen.groups()
    ondalik = float(derece) + float(dakika) / 60 + float(saniye) / 3600
    return -ondalik if yon.upper() in ("S", "W") else ondalik


def parse_coordinate(deger: str | float) -> float:
    """Ondalık sayı ya da DMS metnini kabul eder."""
    if isinstance(deger, (int, float)):
        return float(deger)
    try:
        return float(str(deger).replace(",", "."))
    except ValueError:
        return dms_to_decimal(str(deger))


def haversine_km(lat1, lon1, lat2, lon2):
    """Küre üzerinde büyük daire uzaklığı (km). Dizi girdilerini destekler."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def hypocentral_km(repi_km, depth_km):
    """Hiposantral uzaklık: sqrt(Repi² + derinlik²)."""
    return np.sqrt(np.asarray(repi_km, float) ** 2 + float(depth_km) ** 2)
