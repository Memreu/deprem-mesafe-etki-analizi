"""Deprem kaynağı geometrisi ve uzaklık ölçüleri (Repi, Rhyp, Rjb, Rrup).

* Nokta kaynak: Rjb ≈ Repi, Rrup ≈ Rhyp (küçük depremler için yeterli).
* Sonlu fay (Mw ≥ 6.5 önerilir):
  - 3B çokgen GeoJSON'dan (ör. USGS FFM ya da ShakeMap ``rupture.json``; [boylam, enlem, derinlik_km]) ya da
  - GEM Global Active Faults çizgisi + Thingbaijam vd. (2017) uzunluk/genişlik ölçek yasası.
    Fay izi episantra en yakın GEM izinden başlayarak uç uca eklenen komşu izlerle uzatılır,
    episantrın izdüşümü etrafında L uzunluğunda bir parça kesilir.

Uzaklıklar yerel azimutal eşit uzaklıklı (AEQD) projeksiyonda hesaplanır.
Rjb, fay yüzeyinin yatay izdüşümüne olan uzaklıktır (shapely). Düşey faylarda
Rrup = sqrt(d_iz² + ztor²) olarak shapely ile, eğimli faylarda yüzey 1 km aralıklı
ağ ile hesaplanır.

Kaynaklar: Thingbaijam, Mai & Goda (2017), BSSA 107(5), doi:10.1785/0120170017 —
katsayılar OpenQuake ``scalerel/thingbaijam2017.py``. Styron & Pagani (2020), GEM GAF-DB,
Earthquake Spectra 36(S1), doi:10.1177/8755293020944182.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import substring, unary_union

GEM_TURKEY = Path(__file__).resolve().parent.parent / "data" / "faults" / "gem_active_faults_turkey.geojson"
FINITE_FAULT_MIN_MW = 6.5


# ---------------------------------------------------------------------------
# Ölçek yasaları (Thingbaijam vd. 2017) — OpenQuake uygulaması
# ---------------------------------------------------------------------------
def faulting_style(rake: float) -> str:
    r = ((rake + 180) % 360) - 180
    if 45 < r < 135:
        return "reverse"
    if -135 < r < -45:
        return "normal"
    return "strike_slip"


def thingbaijam2017(mag: float, rake: float) -> tuple[float, float]:
    """Medyan fay uzunluğu ve genişliği (km)."""
    from openquake.hazardlib.scalerel import thingbaijam2017 as t

    cls = {"strike_slip": t.ThingbaijamStrikeSlip, "reverse": t.ThingbaijamReverseFault,
           "normal": t.ThingbaijamNormalFault}[faulting_style(rake)]()
    return float(cls.get_median_length(mag)), float(cls.get_median_width(mag))


# ---------------------------------------------------------------------------
# Projeksiyon
# ---------------------------------------------------------------------------
class LocalProjection:
    """Episantr merkezli AEQD projeksiyonu (km)."""

    def __init__(self, lat0: float, lon0: float):
        crs = f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=km +no_defs"
        self._fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        self._inv = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    def xy(self, lon, lat):
        return self._fwd.transform(lon, lat)

    def lonlat(self, x, y):
        return self._inv.transform(x, y)


# ---------------------------------------------------------------------------
# Kaynak sınıfları
# ---------------------------------------------------------------------------
@dataclass
class Rupture:
    mag: float
    lat: float
    lon: float
    depth: float
    rake: float = 0.0
    # Sonlu fay: her biri (4, 3) köşeli [x, y, z] (km, yerel) dörtgenler
    quads: list[np.ndarray] = field(default_factory=list)
    source: str = "nokta kaynak"
    dip: float = 90.0
    ztor: float = 0.0
    width: float = 0.0
    length: float = 0.0

    def __post_init__(self):
        self.proj = LocalProjection(self.lat, self.lon)

    @property
    def is_finite(self) -> bool:
        return len(self.quads) > 0

    # -- geometri yardımcıları --------------------------------------------
    def surface_projection(self):
        polys = []
        for q in self.quads:
            p = Polygon(q[:, :2])
            polys.append(p if p.area > 1e-6 else LineString(q[[0, 1], :2]).buffer(1e-3))
        return unary_union(polys)

    def trace_lonlat(self) -> list[list[tuple[float, float]]]:
        out = []
        for q in self.quads:
            lo, la = self.proj.lonlat(q[[0, 1], 0], q[[0, 1], 1])
            out.append(list(zip(lo, la)))
        return out

    def outline_lonlat(self):
        geom = self.surface_projection()
        geoms = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
        rings = []
        for g in geoms:
            x, y = g.exterior.xy
            lo, la = self.proj.lonlat(np.array(x), np.array(y))
            rings.append(list(zip(la, lo)))
        return rings

    def _mesh(self, spacing=1.0) -> np.ndarray:
        pts = []
        for q in self.quads:
            p0, p1, p2, p3 = q  # üst-sol, üst-sağ, alt-sağ, alt-sol
            nu = max(int(np.linalg.norm(p1 - p0) / spacing) + 1, 2)
            nv = max(int(np.linalg.norm(p3 - p0) / spacing) + 1, 2)
            u = np.linspace(0, 1, nu)[:, None, None]
            v = np.linspace(0, 1, nv)[None, :, None]
            top = p0 + (p1 - p0) * u
            bot = p3 + (p2 - p3) * u
            pts.append((top + (bot - top) * v).reshape(-1, 3))
        return np.vstack(pts)

    # -- uzaklıklar ---------------------------------------------------------
    def distances(self, lat, lon) -> dict[str, np.ndarray]:
        lat = np.atleast_1d(np.asarray(lat, float))
        lon = np.atleast_1d(np.asarray(lon, float))
        x, y = self.proj.xy(lon, lat)
        x, y = np.asarray(x), np.asarray(y)
        repi = np.hypot(x, y)
        rhyp = np.hypot(repi, self.depth)
        if not self.is_finite:
            return dict(repi=repi, rhyp=rhyp, rjb=repi.copy(), rrup=rhyp.copy())
        footprint = self.surface_projection()
        rjb = np.array([footprint.distance(Point(a, b)) for a, b in zip(x, y)])
        if abs(self.dip - 90.0) < 1e-6:
            lines = unary_union([LineString(q[[0, 1], :2]) for q in self.quads])
            dh = np.array([lines.distance(Point(a, b)) for a, b in zip(x, y)])
            rrup = np.hypot(dh, self.ztor)
        else:
            mesh = self._mesh()
            rrup = np.empty_like(repi)
            for i0 in range(0, len(x), 2000):
                sl = slice(i0, i0 + 2000)
                d = np.sqrt((x[sl, None] - mesh[None, :, 0]) ** 2 + (y[sl, None] - mesh[None, :, 1]) ** 2
                            + mesh[None, :, 2] ** 2)
                rrup[sl] = d.min(axis=1)
        return dict(repi=repi, rhyp=rhyp, rjb=rjb, rrup=rrup)


def point_rupture(mag, lat, lon, depth, rake=0.0) -> Rupture:
    return Rupture(mag=mag, lat=lat, lon=lon, depth=depth, rake=rake)


# ---------------------------------------------------------------------------
# Fay izinden düzlemsel yüzey
# ---------------------------------------------------------------------------
def _quads_from_trace(xy: np.ndarray, dip: float, ztor: float, width: float) -> list[np.ndarray]:
    """İz (N,2) km → dörtgenler. Eğim, iz yönünün sağına doğrudur (Aki–Richards sağ el kuralı)."""
    quads = []
    dz = width * math.sin(math.radians(dip))
    dh = width * math.cos(math.radians(dip))
    for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
        sx, sy = x1 - x0, y1 - y0
        n = math.hypot(sx, sy)
        if n < 1e-6:
            continue
        rx, ry = sy / n, -sx / n  # doğrultunun sağı
        top0 = np.array([x0, y0, ztor])
        top1 = np.array([x1, y1, ztor])
        bot1 = np.array([x1 + rx * dh, y1 + ry * dh, ztor + dz])
        bot0 = np.array([x0 + rx * dh, y0 + ry * dh, ztor + dz])
        quads.append(np.vstack([top0, top1, bot1, bot0]))
    return quads


def rupture_from_trace(mag, lat, lon, depth, trace_lonlat, rake=0.0, dip=90.0, ztor=0.0, width=None,
                       seismogenic_bottom=20.0, source="kullanıcı fay izi") -> Rupture:
    """Verilen fay izinden (boylam, enlem listesi) düzlemsel sonlu fay oluşturur."""
    rup = Rupture(mag=mag, lat=lat, lon=lon, depth=depth, rake=rake, source=source, dip=dip, ztor=ztor)
    if width is None:
        _, width = thingbaijam2017(mag, rake)
    max_w = max((seismogenic_bottom - ztor) / math.sin(math.radians(dip)), 1.0)
    rup.width = min(width, max_w)
    xs, ys = rup.proj.xy(*np.array(trace_lonlat, float).T)
    xy = np.column_stack([xs, ys])
    rup.length = float(LineString(xy).length)
    rup.quads = _quads_from_trace(xy, dip, ztor, rup.width)
    return rup


def rupture_from_geojson(mag, lat, lon, depth, path, rake=0.0, z_scale=None, source=None) -> Rupture:
    """3B çokgenlerden (ShakeMap rupture.json / FFM alt fayları) sonlu fay.

    Her halka [boylam, enlem, derinlik] köşelerinden oluşur. 2n köşeli bir halka, ilk n noktası
    üst kenar, son n noktası (ters sırada) alt kenar olacak şekilde n−1 dörtgene bölünür
    (ShakeMap rupture.json düzeni; 4 köşeli FFM alt fayları da bu düzene uyar).
    ``z_scale`` derinliği km'ye çevirir (ör. metre için 0.001). Verilmezse otomatik seçilir: en büyük derinlik
    100'den büyükse metre kabul edilir (USGS FFM.geojson metre, ShakeMap rupture.json km kullanır).
    """
    gj = json.loads(Path(path).read_text())
    if z_scale is None:
        zs = [c[2] for c in _iter_coords(gj) if len(c) > 2]
        z_scale = 0.001 if zs and max(zs) > 100 else 1.0
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    rup = Rupture(mag=mag, lat=lat, lon=lon, depth=depth, rake=rake, source=source or Path(path).name)
    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = np.array(poly[0], float)
            if ring.ndim != 2 or ring.shape[1] < 3:
                continue
            ring = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
            if len(ring) < 4 or len(ring) % 2:
                continue
            n = len(ring) // 2
            top, bot = ring[:n], ring[n:][::-1]
            for i in range(n - 1):
                c = np.vstack([top[i], top[i + 1], bot[i + 1], bot[i]])
                x, y = rup.proj.xy(c[:, 0], c[:, 1])
                rup.quads.append(np.column_stack([x, y, c[:, 2] * z_scale]))
    if rup.quads:
        rup.ztor = float(min(q[:, 2].min() for q in rup.quads))
        rup.dip = _mean_dip(rup.quads)
        # Uzunluk: en sığ sıradaki dörtgenlerin üst kenar uzunlukları toplamı (FFM ızgarasında yalnızca üst sıra)
        top = [q for q in rup.quads if q[:2, 2].min() <= rup.ztor + 0.5]
        rup.length = float(sum(np.linalg.norm(q[1, :2] - q[0, :2]) for q in top))
        rup.width = float(np.mean([np.linalg.norm(q[3] - q[0]) for q in rup.quads]))
    return rup


def _iter_coords(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_coords(v)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, (int, float)) for x in obj):
            yield obj
        else:
            for v in obj:
                yield from _iter_coords(v)


def _mean_dip(quads) -> float:
    dips = []
    for q in quads:
        dz = abs(q[3, 2] - q[0, 2])
        dh = np.linalg.norm(q[3, :2] - q[0, :2])
        dips.append(math.degrees(math.atan2(dz, dh)) if dh > 0 else 90.0)
    return float(np.mean(dips))


# ---------------------------------------------------------------------------
# GEM aktif fay veritabanından otomatik sonlu fay
# ---------------------------------------------------------------------------
def _first_number(s, default):
    if s is None:
        return default
    if isinstance(s, (int, float)):
        return float(s)
    m = re.search(r"-?\d+(\.\d+)?", str(s))
    return float(m.group()) if m else default


def load_gem_faults(path=GEM_TURKEY) -> list[dict]:
    gj = json.loads(Path(path).read_text())
    out = []
    for f in gj["features"]:
        p = f["properties"]
        out.append(dict(coords=np.array(f["geometry"]["coordinates"], float)[:, :2],
                        dip=_first_number(p.get("average_dip"), 90.0),
                        rake=_first_number(p.get("average_rake"), 0.0),
                        usd=_first_number(p.get("upper_seis_depth"), 0.0),
                        lsd=_first_number(p.get("lower_seis_depth"), 20.0),
                        slip_type=p.get("slip_type"), catalog_id=p.get("catalog_id")))
    return out


def _azimuth(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360


def _ang_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _chain_traces(start: np.ndarray, others: list[np.ndarray], gap_km=10.0, max_turn=50.0, max_len=600.0):
    """Başlangıç izini, uçlarına yakın ve benzer doğrultulu izlerle iki yönde uzatır."""
    chain = start.copy()
    used = set()
    for _ in range(60):
        if LineString(chain).length > max_len:
            break
        best = None
        for j, o in enumerate(others):
            if j in used or len(o) < 2:
                continue
            for end in ("head", "tail"):
                cp = chain[0] if end == "head" else chain[-1]
                caz = _azimuth(chain[1], chain[0]) if end == "head" else _azimuth(chain[-2], chain[-1])
                for flip in (False, True):
                    oo = o[::-1] if flip else o
                    # eklenecek iz, zincir ucundan dışa doğru ilerlemeli
                    near = oo[-1] if end == "head" else oo[0]
                    d = math.hypot(*(near - cp))
                    if d > gap_km:
                        continue
                    oaz = _azimuth(oo[-1], oo[-2]) if end == "head" else _azimuth(oo[0], oo[1])
                    oaz_all = _azimuth(oo[-1], oo[0]) if end == "head" else _azimuth(oo[0], oo[-1])
                    if _ang_diff(caz, oaz) > max_turn or _ang_diff(caz, oaz_all) > max_turn:
                        continue
                    score = d + 0.1 * _ang_diff(caz, oaz)
                    if best is None or score < best[0]:
                        best = (score, j, end, oo)
        if best is None:
            break
        _, j, end, oo = best
        used.add(j)
        chain = np.vstack([oo, chain]) if end == "head" else np.vstack([chain, oo])
    return chain, used


def rupture_from_gem(mag, lat, lon, depth, rake=None, faults=None, search_km=25.0, gap_km=10.0) -> Rupture:
    """Episantra en yakın GEM fay izini kullanarak Thingbaijam (2017) boyutlu sonlu fay kurar.

    Episantra ``search_km`` içinde iz yoksa nokta kaynağa döner.
    """
    faults = faults if faults is not None else load_gem_faults()
    proj = LocalProjection(lat, lon)
    proj_coords = []
    for f in faults:
        x, y = proj.xy(f["coords"][:, 0], f["coords"][:, 1])
        proj_coords.append(np.column_stack([x, y]))
    origin = Point(0, 0)
    dists = np.array([LineString(c).distance(origin) if len(c) > 1 else 1e9 for c in proj_coords])
    cand = np.where(dists <= search_km)[0]
    if cand.size == 0:
        return point_rupture(mag, lat, lon, depth, rake or 0.0)
    # Her aday iz için zincir kur; L'yi taşıyabilen ve episantra yakın zinciri seç.
    # Puan = uzaklık (km) + 50·(1 − min(zincir, L)/L). Büyük depremler kısa yan kollar yerine
    # ana fay zonunu kırma eğiliminde olduğundan, L'yi taşıyamayan kısa izler cezalandırılır.
    best = None
    for i in cand:
        f = faults[i]
        rk = f["rake"] if rake is None else rake
        L, W = thingbaijam2017(mag, rk)
        others = [c for k, c in enumerate(proj_coords) if k != i]
        chain, _ = _chain_traces(proj_coords[i], others, gap_km=gap_km, max_len=3 * L)
        Lc = LineString(chain).length
        score = dists[i] + 50.0 * (1.0 - min(Lc, L) / L)
        if best is None or score < best[0]:
            best = (score, i, chain, rk, L, W)
    _, i0, chain, rake, length, width = best
    f0 = faults[i0]
    line = LineString(chain)
    s0 = line.project(origin)
    a, b = s0 - length / 2, s0 + length / 2
    if a < 0:
        a, b = 0.0, min(line.length, b - a)
    if b > line.length:
        a, b = max(0.0, a - (b - line.length)), line.length
    seg = substring(line, a, b)
    xy = np.asarray(seg.coords)
    lo, la = proj.lonlat(xy[:, 0], xy[:, 1])
    return rupture_from_trace(mag, lat, lon, depth, list(zip(lo, la)), rake=rake, dip=f0["dip"], ztor=f0["usd"],
                              width=width, seismogenic_bottom=f0["lsd"],
                              source=f"GEM GAF-DB izi ({f0['catalog_id']}) + Thingbaijam 2017")


def build_rupture(mag, lat, lon, depth, rake=None, rupture_geojson=None, z_scale=None, use_finite=None) -> Rupture:
    """Önerilen varsayılan: FFM/rupture dosyası varsa onu, yoksa Mw ≥ 6.5 için GEM tabanlı sonlu fay."""
    if rupture_geojson:
        return rupture_from_geojson(mag, lat, lon, depth, rupture_geojson, rake=rake or 0.0, z_scale=z_scale)
    if use_finite is None:
        use_finite = mag >= FINITE_FAULT_MIN_MW
    if use_finite:
        return rupture_from_gem(mag, lat, lon, depth, rake=rake)
    return point_rupture(mag, lat, lon, depth, rake or 0.0)
