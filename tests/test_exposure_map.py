import numpy as np
import pytest

from mmi_mapper.exposure import PAGER_BINS, pager_table
from mmi_mapper.model import Event


def test_pager_table_bins_sum_population():
    mmi = np.array([1.0, 3.0, 5.2, 6.6, 7.6, 9.9])
    pop = np.array([10, 20, 30, 40, 50, 60.0])
    t = pager_table({"Medyan": mmi}, pop)
    assert list(t.MMI) == [b[0] for b in PAGER_BINS]
    assert t.Medyan.sum() == pop.sum()
    assert t.set_index("MMI").loc["VII", "Medyan"] == 40


def test_layered_map_and_exposure_small():
    pytest.importorskip("geonamescache")
    from mmi_mapper.exposure import exposure
    from mmi_mapper.grid import run_latlon_grid
    from mmi_mapper.mapping import layered_map

    ev = Event(6.0, 38.4, 39.1, 10.0)
    g, rup = run_latlon_grid(ev, 0.5, 0.1)
    assert not rup.is_finite  # Mw < 6.5 → nokta kaynak
    table, places, _ = exposure(ev, 0.7, rupture=rup)
    assert table.Medyan.sum() == pytest.approx(places.population.sum())
    html = layered_map(ev, g, rup, places=places).get_root().render()
    assert "Medyan MMI" in html and html.count("ImageOverlay") + html.count("imageOverlay") >= 6


def test_cli_noninteractive(tmp_path):
    from mmi_mapper.cli import main

    out = tmp_path / "m.html"
    main(["--mag", "6.0", "--lat", "38.4", "--lon", "39.1", "--site", "38.67,39.22", "--vs30", "400",
          "--html", str(out), "--no-browser"])
    assert out.exists()
