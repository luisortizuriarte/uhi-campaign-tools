"""Unit tests for analysis plotting routines (scatter, bar, boxplot) supporting temperature and anomaly."""

import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import uhi
from uhi.analysis import (
    SLIDE_FIGSIZE,
    plot_scatter_canopy_temp,
    plot_grouped_barchart,
    plot_single_barchart,
    plot_grouped_boxplot,
    plot_single_boxplot,
    QUINTILE_SHORT_LABELS,
)


class TestAnalysisPlots(unittest.TestCase):
    """Test suite for analysis charts."""

    def setUp(self):
        np.random.seed(42)
        n = 500
        canopy = np.random.uniform(0, 100, n)
        # Create synthetic temperatures correlated with canopy
        temp_am = 82.0 - 0.03 * canopy + np.random.normal(0, 1.0, n)
        temp_af = 97.0 - 0.04 * canopy + np.random.normal(0, 1.0, n)
        temp_pm = 95.0 - 0.05 * canopy + np.random.normal(0, 1.0, n)

        self.df = pd.DataFrame({
            "canopy_pct": canopy,
            "temp_am": temp_am,
            "temp_af": temp_af,
            "temp_pm": temp_pm,
            "anom_am": temp_am - temp_am.mean(),
            "anom_af": temp_af - temp_af.mean(),
            "anom_pm": temp_pm - temp_pm.mean(),
        })
        self.df["quintile"] = pd.cut(
            self.df["canopy_pct"],
            bins=[0, 20, 40, 60, 80, 100],
            include_lowest=True,
            labels=QUINTILE_SHORT_LABELS,
        )

    def test_plot_scatter_temperature(self):
        fig, ax = plot_scatter_canopy_temp(self.df, "temp_am", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_scatter_anomaly(self):
        fig, ax = plot_scatter_canopy_temp(self.df, "anom_af", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_grouped_barchart_temperature(self):
        fig, ax = plot_grouped_barchart(self.df, cols=["temp_am", "temp_af", "temp_pm"], dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_grouped_barchart_anomaly(self):
        fig, ax = plot_grouped_barchart(self.df, cols=["anom_am", "anom_af", "anom_pm"], dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_single_barchart_temperature(self):
        fig, ax = plot_single_barchart(self.df, "temp_af", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_single_barchart_anomaly(self):
        fig, ax = plot_single_barchart(self.df, "anom_pm", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_grouped_boxplot_temperature(self):
        fig, ax = plot_grouped_boxplot(self.df, cols=["temp_am", "temp_af", "temp_pm"], dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_grouped_boxplot_anomaly(self):
        fig, ax = plot_grouped_boxplot(self.df, cols=["anom_am", "anom_af", "anom_pm"], dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_single_boxplot_temperature(self):
        fig, ax = plot_single_boxplot(self.df, "temp_pm", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)

    def test_plot_single_boxplot_anomaly(self):
        fig, ax = plot_single_boxplot(self.df, "anom_am", dpi=72)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        plt.close(fig)


if __name__ == "__main__":
    unittest.main()
