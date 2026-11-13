"""Unit tests for multi-variable (temperature and heat_index) support."""

from pathlib import Path
import unittest

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
from shapely.geometry import Point

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import uhi.analysis as analysis  # noqa: E402
from uhi.io import extract_period  # noqa: E402
from uhi.school_analysis import (  # noqa: E402
    plot_hottest_to_coldest_schools,
    plot_school_canopy_vs_anomaly,
)
from uhi.variables import get_variable_spec  # noqa: E402
from uhi.zonal import HEAT_INDEX_PERIODS  # noqa: E402


class TestVariablesRegistry(unittest.TestCase):
    """Tests for uhi.variables registry and raster filename mappings."""

    def test_get_variable_spec_temperature_and_heat_index(self) -> None:
        temp_spec = get_variable_spec("temperature")
        hi_spec = get_variable_spec("heat_index")

        self.assertEqual(temp_spec.key, "temperature")
        self.assertEqual(temp_spec.grid_output_gpkg, Path("output/temperature/grid-temp.gpkg"))
        self.assertNotEqual(temp_spec.grid_output_gpkg, temp_spec.grid_input_gpkg)
        self.assertEqual(temp_spec.hotspots_dir, Path("output/temperature/hotspots"))
        self.assertEqual(temp_spec.locations_dir, Path("output/temperature/locations"))
        self.assertEqual(temp_spec.figures_dir, Path("output/figures/air_temperature"))

        self.assertEqual(hi_spec.key, "heat_index")
        self.assertEqual(hi_spec.display_name, "Heat Index")
        self.assertEqual(hi_spec.abbr, "HI")
        self.assertEqual(hi_spec.unit, "°F")
        self.assertEqual(hi_spec.grid_output_gpkg, Path("output/heat_index/grid-hi.gpkg"))
        self.assertNotEqual(hi_spec.grid_output_gpkg, hi_spec.grid_input_gpkg)
        self.assertEqual(hi_spec.figures_dir, Path("output/figures/heat_index"))
        self.assertEqual(
            hi_spec.input_rasters,
            {
                "am": "full-am-hi.tif",
                "af": "full-af-hi.tif",
                "pm": "full-pm-hi.tif",
            },
        )
        with self.assertRaises(ValueError):
            get_variable_spec("humidity")

    def test_extract_period_heat_index_and_zonal_spec(self) -> None:
        self.assertEqual(extract_period("full-am-hi.tif"), "am")
        self.assertEqual(extract_period("full-af-hi.tif"), "af")
        self.assertEqual(extract_period("full-pm-hi.tif"), "pm")
        self.assertEqual(
            HEAT_INDEX_PERIODS,
            [
                ("am", "temp_am", "full-am-hi.tif"),
                ("af", "temp_af", "full-af-hi.tif"),
                ("pm", "temp_pm", "full-pm-hi.tif"),
            ],
        )


class TestHeatIndexPlotting(unittest.TestCase):
    """Tests verifying Heat Index dynamic y-limits and labels across plotting modules."""

    def setUp(self) -> None:
        rng = np.random.default_rng(42)
        n_per_q = 40
        n = n_per_q * len(analysis.QUINTILE_SHORT_LABELS)
        q_idx = np.repeat(np.arange(len(analysis.QUINTILE_SHORT_LABELS)), n_per_q)
        quintile_col = pd.Categorical.from_codes(
            q_idx, categories=analysis.QUINTILE_SHORT_LABELS, ordered=True
        )
        canopy = np.clip(q_idx * 20.0 + rng.uniform(0.5, 19.5, size=n), 0.0, 100.0)

        # Synthetic Heat Index values around 84 / 106 / 102 °F with wide AM anomaly
        self.df = pd.DataFrame(
            {
                "canopy_pct": canopy,
                "quintile": quintile_col,
                "temp_am": 87.5 - 0.11 * canopy + rng.normal(0.0, 0.7, size=n),
                "temp_af": 108.5 - 0.06 * canopy + rng.normal(0.0, 0.6, size=n),
                "temp_pm": 104.0 - 0.05 * canopy + rng.normal(0.0, 0.5, size=n),
            }
        )
        for p in ("am", "af", "pm"):
            self.df[f"anom_{p}"] = self.df[f"temp_{p}"] - self.df[f"temp_{p}"].mean()

        n_schools = 24
        school_canopy = np.linspace(5.0, 65.0, n_schools)
        self.schools_gdf = gpd.GeoDataFrame(
            {
                "school_name": [f"Sample School {i}" for i in range(n_schools)],
                "jurisdiction": ["Fairfax"] * 12 + ["Arlington"] * 12,
                "school_type": ["Public"] * n_schools,
                "canopy_pct": school_canopy,
                "temp_med_am": 89.0 - 0.14 * school_canopy,
                "temp_med_af": 110.5 - 0.09 * school_canopy,
                "temp_med_pm": 105.0 - 0.07 * school_canopy,
                "anom_med_am": np.linspace(4.8, -5.0, n_schools),
                "anom_med_af": np.linspace(3.5, -2.5, n_schools),
                "anom_med_pm": np.linspace(2.6, -2.2, n_schools),
            },
            geometry=[Point(300000 + i * 500, 4300000) for i in range(n_schools)],
            crs="EPSG:32618",
        )

    def test_analysis_charts_dynamic_limits_for_heat_index(self) -> None:
        figs = []
        try:
            fig_bar, ax_bar = analysis.plot_grouped_barchart(
                self.df,
                cols=["temp_am", "temp_af", "temp_pm"],
                variable="heat_index",
            )
            figs.append(fig_bar)
            ymin, ymax = ax_bar.get_ylim()
            self.assertGreater(ymax, 108.0)
            self.assertLess(ymin, 80.0)
            all_text = " ".join(t.get_text() for t in fig_bar.texts)
            self.assertIn("Heat Index", all_text)

            fig_box, ax_box = analysis.plot_grouped_boxplot(
                self.df,
                cols=["anom_am", "anom_af", "anom_pm"],
                variable="heat_index",
            )
            figs.append(fig_box)
            aymin, aymax = ax_box.get_ylim()
            self.assertGreaterEqual(aymax, 4.0)
            self.assertLessEqual(aymin, -4.0)

            fig_scat, _ = analysis.plot_scatter_canopy_temp(
                self.df,
                "temp_af",
                variable="heat_index",
            )
            figs.append(fig_scat)
            scat_text = " ".join(t.get_text() for t in fig_scat.texts)
            self.assertIn("Heat Index", scat_text)
        finally:
            for fig in figs:
                plt.close(fig)

    def test_school_charts_dynamic_limits_for_heat_index(self) -> None:
        figs = []
        try:
            fig_bar = plot_hottest_to_coldest_schools(
                self.schools_gdf,
                period="af",
                n_top=10,
                variable="heat_index",
            )
            figs.append(fig_bar)
            text_all = " ".join(t.get_text() for t in fig_bar.texts)
            self.assertIn("Heat Index", text_all)
            ax = fig_bar.axes[0]
            self.assertGreater(ax.get_xlim()[1], 108.0)

            fig_scat = plot_school_canopy_vs_anomaly(
                self.schools_gdf,
                variable="heat_index",
            )
            figs.append(fig_scat)
            ax_s = fig_scat.axes[0]
            ymin, ymax = ax_s.get_ylim()
            self.assertGreaterEqual(ymax, 5.0)
            self.assertLessEqual(ymin, -5.0)
            scat_text = " ".join(t.get_text() for t in fig_scat.texts)
            self.assertIn("Heat Index", scat_text)
        finally:
            for fig in figs:
                plt.close(fig)


if __name__ == "__main__":
    unittest.main()
