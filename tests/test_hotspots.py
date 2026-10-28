"""
tests/test_hotspots.py - Unit tests for spatial hot and cold spot analysis.
"""

import numpy as np
import pandas as pd
import unittest

from uhi.hotspots import (
    compute_gi_star_grid,
    fdr_correction,
    analyze_hotspots,
    summarize_hotspots_by_period,
    summarize_persistence,
    summarize_canopy_comparison,
    compare_methods_sensitivity,
)


def test_compute_gi_star_synthetic():
    """Verify Gi* correctly identifies hot and cold clusters in synthetic grid."""
    np.random.seed(42)
    # 15x15 baseline random noise around 70.0
    grid = np.random.normal(70.0, 1.0, (15, 15))
    
    # Inject a 3x3 hot cluster in top-left
    grid[1:4, 1:4] = 95.0
    # Inject a 3x3 cold cluster in bottom-right
    grid[11:14, 11:14] = 45.0

    gi_z, p_vals = compute_gi_star_grid(grid)

    assert gi_z.shape == (15, 15)
    assert p_vals.shape == (15, 15)

    # Center of hot cluster should have large positive z-score
    hot_center_z = gi_z[2, 2]
    assert hot_center_z > 2.5
    assert p_vals[2, 2] < 0.01

    # Center of cold cluster should have large negative z-score
    cold_center_z = gi_z[12, 12]
    assert cold_center_z < -2.5
    assert p_vals[12, 12] < 0.01


def test_fdr_correction():
    """Verify FDR correction operates correctly on p-values."""
    p_vals = np.array([0.0001, 0.001, 0.01, 0.04, 0.05, 0.2, 0.8, np.nan])
    q_vals = fdr_correction(p_vals, q=0.05)

    assert np.isnan(q_vals[-1])
    # Monotonicity check
    valid_q = q_vals[:-1]
    assert np.all(valid_q[1:] >= valid_q[:-1])
    # The smallest p-value should remain highly significant
    assert valid_q[0] < 0.01


def test_nan_handling_in_gi_star():
    """Verify that NaNs in the grid do not cause crashes or NaN propagation."""
    grid = np.full((10, 10), 80.0)
    grid[0, 0] = np.nan
    grid[5, 5] = np.nan
    grid[2:4, 2:4] = 95.0

    mask = np.isfinite(grid)
    gi_z, p_vals = compute_gi_star_grid(grid, valid_mask=mask)

    assert np.isnan(gi_z[0, 0])
    assert np.isnan(gi_z[5, 5])
    # Neighbor of NaN should still have valid finite calculation
    assert np.isfinite(gi_z[0, 1])
    assert np.isfinite(gi_z[5, 6])


def test_persistence_classification():
    """Verify persistence classification correctly assigns categories."""
    n = 25
    df = pd.DataFrame({
        "id": np.arange(n),
        "row_index": np.tile(np.arange(5), 5),
        "col_index": np.repeat(np.arange(5), 5),
        "left": np.arange(n),
        "right": np.arange(n) + 100,
        "top": np.arange(n) + 100,
        "bottom": np.arange(n),
        "temp_am": np.full(n, 70.0),
        "temp_af": np.full(n, 70.0),
        "temp_pm": np.full(n, 70.0),
        "canopy_pct": np.linspace(10, 90, n),
    })

    # Set a 2x2 cluster of cells [0, 1, 5, 6] to hot across all periods
    df.loc[[0, 1, 5, 6], ["temp_am", "temp_af", "temp_pm"]] = 110.0
    # Set a 2x2 cluster of cells [18, 19, 23, 24] to cold across all periods
    df.loc[[18, 19, 23, 24], ["temp_am", "temp_af", "temp_pm"]] = 30.0

    res = analyze_hotspots(df)

    assert "persistence" in res.columns
    assert "hot_all3" in res.columns
    assert "cold_all3" in res.columns
    assert res.loc[0, "hot_all3"] == True
    assert res.loc[0, "persistence"] == "Hot Spot (All 3 Times)"
    assert res.loc[24, "cold_all3"] == True
    assert res.loc[24, "persistence"] == "Cold Spot (All 3 Times)"


def test_summaries_generation():
    """Verify that summary functions produce valid non-empty DataFrames."""
    n = 25
    df = pd.DataFrame({
        "id": np.arange(n),
        "row_index": np.tile(np.arange(5), 5),
        "col_index": np.repeat(np.arange(5), 5),
        "left": np.arange(n),
        "right": np.arange(n) + 100,
        "top": np.arange(n) + 100,
        "bottom": np.arange(n),
        "temp_am": np.random.normal(80, 2, n),
        "temp_af": np.random.normal(95, 2, n),
        "temp_pm": np.random.normal(90, 2, n),
        "canopy_pct": np.random.uniform(10, 90, n),
    })
    # inject hot cell
    df.loc[0, ["temp_am", "temp_af", "temp_pm"]] = 130.0
    res = analyze_hotspots(df)

    s_period = summarize_hotspots_by_period(res)
    assert len(s_period) > 0
    assert "area_km2" in s_period.columns

    s_pers = summarize_persistence(res)
    assert len(s_pers) > 0
    assert "persistence_class" in s_pers.columns

    canopy_res = summarize_canopy_comparison(res)
    assert "stats_table" in canopy_res
    assert "p_value" in canopy_res

    s_sens = compare_methods_sensitivity(res)
    assert len(s_sens) > 0
    assert "share_of_percentile_confirmed_by_gi" in s_sens.columns
