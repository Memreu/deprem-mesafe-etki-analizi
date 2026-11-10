import numpy as np
import pandas as pd
import pytest

pytest.importorskip("lightgbm")

from mmi_mapper import ml  # noqa: E402


def _synthetic(n=400, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        "event_id": rng.integers(0, 60, n).astype(str), "mag": rng.uniform(4.5, 7.5, n),
        "rrup": 10 ** rng.uniform(0.7, 2.5, n), "vs30": rng.uniform(200, 900, n),
        "ev_depth_km": rng.uniform(3, 30, n), "lat": rng.uniform(36, 41, n), "lon": rng.uniform(27, 44, n)})
    d["window_group"] = d.event_id
    d[ml.BACKBONE] = 1.5 * d.mag - 2.0 * np.log10(d.rrup)
    d["obs_mmi"] = d[ml.BACKBONE] - 0.4 + 0.3 * (d.lat > 38.5) + rng.normal(0, 0.3, n)
    return d


def test_hybrid_beats_backbone_and_is_monotonic(tmp_path):
    d = _synthetic()
    oof, folds = ml.grouped_cv(d, n_splits=4)
    assert ml.rmse(oof.obs_mmi - oof.hybrid) < ml.rmse(oof.obs_mmi - oof[ml.BACKBONE])
    # GroupKFold: aynı grup hem eğitimde hem testte olmamalı → kat sayısı kadar satır grubu
    assert folds.kat.nunique() == 4
    m = ml.ResidualModel().fit(d)
    assert all(ml.check_monotonic(m, d).values())
    m.save(tmp_path / "m.txt")
    m2 = ml.ResidualModel.load(tmp_path / "m.txt")
    np.testing.assert_allclose(m.correction(d.head(20)), m2.correction(d.head(20)), atol=1e-6)
