import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from mmi_mapper.uncertainty import LogicTree, add_uncertainty, exceedance, mixture_quantile


def test_single_normal_quantiles_and_exceedance():
    mu, sd = np.array([7.0]), np.array([0.8])
    assert mixture_quantile(0.84, [mu], [sd], [1.0])[0] == pytest.approx(7 + norm.ppf(0.84) * 0.8, abs=1e-3)
    assert exceedance(mu, sd, 7.0)[0] == pytest.approx(0.5)
    # literatür taramasındaki tanım: P(MMI ≥ VIII) = 1 − Φ((8 − μ)/σ)
    assert exceedance(mu, sd, 8.0)[0] == pytest.approx(1 - norm.cdf((8 - 7) / 0.8))


def test_mixture_properties():
    df = pd.DataFrame({
        "allen2012_rrup": [6.0, 8.0], "allen2012_rrup_sd": [0.8, 0.9],
        "kale2015_wgrw12": [6.5, 7.5], "kale2015_wgrw12_sd": [1.0, 1.0],
        "kale2015_ba14": [5.5, 7.0], "kale2015_ba14_sd": [1.0, 1.0],
        "bayrak2019": [6.2, 7.8], "bayrak2019_sd": [1.27, 1.27],
    })
    out = add_uncertainty(df, LogicTree(), finite=False)
    assert np.all(out.lt_p16 < out.lt_p50) and np.all(out.lt_p50 < out.lt_p84)
    assert np.all((out.p_ge_8 <= out.p_ge_7) & (out.p_ge_7 <= 1) & (out.p_ge_8 >= 0))
    assert sum(out.attrs["logic_tree_weights"].values()) == pytest.approx(1.0)
    assert len(out.attrs["logic_tree_weights"]) >= 3


def test_finite_fault_downweights_bayrak():
    w = LogicTree().effective(finite=True)
    assert w["bayrak2019"] < 0.06 and sum(w.values()) == pytest.approx(1.0)
