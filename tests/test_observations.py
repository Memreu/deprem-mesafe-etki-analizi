import json

import numpy as np
import pytest

from mmi_mapper import observations as O
from mmi_mapper.benchmark import metrics, predict_for_observations
from mmi_mapper.model import Event


def test_dyfi_parser_with_comment_header(tmp_path):
    f = tmp_path / "cdi_geo.txt"
    # USGS cdi_geo.txt biçimi (us6000jllz dosyasından örnek satır yapısı)
    f.write_text("# Columns: Geocoded box,CDI,No. of responses,Hypocentral distance,Latitude,Longitude,Suspect?,"
                 "Standard deviation,City,State\n"
                 '"UTM:(37S 0300 4120 1000)",7.1,12,40,37.2,37.0,0,0.2,"UTM:(37S 0300 4120 1000)",""\n'
                 '"UTM:(37S 0310 4120 1000)",5.0,1,90,37.5,37.4,0,0.3,"x, y",""\n'
                 '"UTM:(37S 0320 4120 1000)",8.0,9,90,37.6,37.4,1,0.3,"z",""\n')
    d = O.load_dyfi(f, min_responses=3)
    assert len(d) == 1 and d.obs_mmi.iloc[0] == pytest.approx(7.1)  # 1 yanıtlı ve şüpheli hücreler atılır


def test_shakemap_stationlist_channels(tmp_path):
    gj = {"type": "FeatureCollection", "features": [
        {"geometry": {"type": "Point", "coordinates": [37.1, 37.3]},
         "properties": {"code": "4615", "network": "TK", "station_type": "seismic", "vs30": 300,
                        "channels": [{"amplitudes": [{"name": "pgv", "value": 80.0}]},
                                     {"amplitudes": [{"name": "pgv", "value": 95.0}]}]}},
        {"geometry": {"type": "Point", "coordinates": [37.0, 37.0]},
         "properties": {"code": "X", "network": "KO", "pgv": 10.0}}]}
    f = tmp_path / "stationlist.json"
    f.write_text(json.dumps(gj))
    d = O.load_shakemap_stations(f, networks=("TK",))
    assert len(d) == 1 and d.pgv_cms.iloc[0] == 95.0 and 8.5 < d.obs_mmi.iloc[0] <= 10


def test_koeri_benchmark_small_event():
    k = O.load_koeri(min_mw=6.0)
    eid = k.event_id.iloc[0]
    r = k[k.event_id == eid].iloc[0]
    res, _ = predict_for_observations(Event(r.mw, r.ev_lat, r.ev_lon, r.ev_depth_km, event_id=eid),
                                      k[k.event_id == eid])
    m = metrics(res)
    assert {"sapma", "RMSE"} <= set(m.columns) and np.isfinite(m.RMSE).all()


def test_ffm_depth_in_meters_autodetected(tmp_path):
    from mmi_mapper.rupture import rupture_from_geojson

    ring = [[37.0, 37.0, 1000.0], [37.2, 37.1, 1000.0], [37.21, 37.08, 6000.0], [37.01, 36.98, 6000.0],
            [37.0, 37.0, 1000.0]]
    f = tmp_path / "FFM.geojson"
    f.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}))
    r = rupture_from_geojson(7.0, 37.0, 37.0, 10.0, f)
    assert r.ztor == pytest.approx(1.0) and max(q[:, 2].max() for q in r.quads) == pytest.approx(6.0)
