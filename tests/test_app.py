"""Streamlit arayüzü ve olay modülü için duman testleri."""

from pathlib import Path

import numpy as np
import pytest

from mmi_mapper import events as E

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def test_events_table_and_ruptures():
    evs = E.load_events()
    assert len(evs) == 6
    for eid in evs.index:
        f = E.rupture_file(eid, evs)
        assert f is None or f.exists()
    # Düzce 1999'da USGS fayı yok: 'auto' otomatik GEM fayına düşer
    assert E.rupture_file("usp0009hev", evs) is None
    assert E.event_rupture("usp0009hev", "auto", evs).is_finite
    assert not E.event_rupture("us6000jllz", "point", evs).is_finite
    with pytest.raises(ValueError):
        E.event_rupture("us6000jllz", "yok")


def test_usgs_observations_counts():
    obs = E.usgs_observations("us6000jllz")
    assert len(obs) == 447 and np.isfinite(obs.obs_mmi).all()


@pytest.fixture(scope="module")
def app():
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file(str(APP), default_timeout=600)
    at.run()
    return at


def test_app_runs_with_all_presets(app):
    assert not app.exception
    options = app.sidebar.selectbox[0].options
    assert len(options) == 7  # altı deprem + özel senaryo


def test_app_shows_observation_metrics(app):
    # Varsayılan senaryo Kahramanmaraş Mw 7.8: USGS fayı ve 447 gözlem
    assert app.sidebar.radio[0].value == "auto"
    labels = [m.label for m in app.metric]
    assert "Gözlemlere karşı RMSE" in labels
    rmse = float(app.metric[labels.index("Gözlemlere karşı RMSE")].value.split()[0])
    assert 0.5 < rmse < 1.2  # README: Pazarcık için mantık ağacı RMSE 0,85


def test_app_custom_scenario(app):
    app.sidebar.selectbox[0].select("Özel senaryo").run()
    assert not app.exception
    assert any("gözlem yok" in i.value for i in app.info)


def test_cli_event_uses_usgs_fault(capsys):
    from mmi_mapper.cli import main

    main(["--list-events"])
    assert "usp0009hev" in capsys.readouterr().out
    main(["--event", "us6000jllz", "--site", "37.5753,36.9228", "--html", "", "--no-browser"])
    out = capsys.readouterr().out
    assert "us6000jllz_shakemap.geojson" in out and "Mantık ağacı" in out
