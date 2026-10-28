"""
Unit tests for uhi.school_analysis module.
"""

import unittest
from pathlib import Path
import tempfile
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point

from uhi.school_analysis import (
    plot_hottest_to_coldest_schools,
    plot_school_canopy_vs_anomaly,
    compute_school_buffer_metrics,
    DEFAULT_BUFFERS_GPKG,
)


class TestSchoolAnalysis(unittest.TestCase):
    def setUp(self):
        # Create a mock GeoDataFrame for fast plotting tests
        points = [Point(320000 + i * 100, 4300000 + i * 100) for i in range(25)]
        self.mock_df = gpd.GeoDataFrame(
            {
                "school_name": [f"School {i}" for i in range(25)],
                "jurisdiction": ["Fairfax"] * 15 + ["Arlington"] * 5 + ["Alexandria"] * 5,
                "county_code": ["FFX"] * 15 + ["ARL"] * 5 + ["ALX"] * 5,
                "temp_med_am": [80.0 + i * 0.15 for i in range(25)],
                "temp_med_af": [94.0 + i * 0.20 for i in range(25)],
                "temp_med_pm": [92.0 + i * 0.25 for i in range(25)],
                "anom_med_am": [-0.6 + i * 0.05 for i in range(25)],
                "anom_med_af": [-1.4 + i * 0.10 for i in range(25)],
                "anom_med_pm": [-1.0 + i * 0.12 for i in range(25)],
                "canopy_pct": [65.0 - i * 1.5 for i in range(25)],
                "geometry": [p.buffer(500.0) for p in points],
            },
            crs="EPSG:32618",
        )

    def test_plot_hottest_to_coldest_schools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_hottest_af.png"
            fig = plot_hottest_to_coldest_schools(
                self.mock_df,
                period="af",
                output_path=out_file,
                n_top=5,
            )
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_file.is_file())
            plt.close(fig)

    def test_plot_school_canopy_vs_anomaly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_canopy_anom.png"
            fig = plot_school_canopy_vs_anomaly(
                self.mock_df,
                output_path=out_file,
            )
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_file.is_file())
            plt.close(fig)

    def test_existing_buffers_gpkg(self):
        # Verify the actual production buffers file if present
        if DEFAULT_BUFFERS_GPKG.is_file():
            gdf = gpd.read_file(DEFAULT_BUFFERS_GPKG)
            self.assertEqual(len(gdf), 261)
            self.assertTrue("temp_med_am" in gdf.columns)
            self.assertTrue("temp_med_af" in gdf.columns)
            self.assertTrue("temp_med_pm" in gdf.columns)
            self.assertTrue("canopy_pct" in gdf.columns)
            self.assertTrue((gdf.geom_type == "Polygon").all())


if __name__ == "__main__":
    unittest.main()

