"""Unit tests for temperature zonal mean computation."""

import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

import uhi
from uhi.zonal import compute_temperature_zonal_means


class TestTemperatureZonal(unittest.TestCase):
    """Test suite for zonal mean temperature extraction."""

    def setUp(self):
        # 2x2 grid of 100m cells: (x0=300000, y0=4300000)
        polys = []
        ids, rows, cols = [], [], []
        lefts, tops, rights, bottoms = [], [], [], []

        cell_size = 100.0
        x0, y0 = 300000.0, 4300000.0
        count = 1
        for r in range(2):
            for c in range(2):
                l = x0 + c * cell_size
                t = y0 - r * cell_size
                polys.append(box(l, t - cell_size, l + cell_size, t))
                ids.append(count)
                rows.append(r)
                cols.append(c)
                lefts.append(l)
                tops.append(t)
                rights.append(l + cell_size)
                bottoms.append(t - cell_size)
                count += 1

        self.grid_gdf = gpd.GeoDataFrame(
            {
                "id": ids,
                "left": lefts,
                "top": tops,
                "right": rights,
                "bottom": bottoms,
                "row_index": rows,
                "col_index": cols,
            },
            geometry=polys,
            crs="EPSG:32618",
        )

    def test_zonal_mean_calculation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create 10m synthetic rasters for AM, AF, PM (20x20 pixels covering 200mx200m)
            # Cell (0, 0) top-left 10x10 pixels
            # Cell (0, 1) top-right 10x10 pixels
            # Cell (1, 0) bottom-left 10x10 pixels
            # Cell (1, 1) bottom-right 10x10 pixels
            transform = from_origin(300000.0, 4300000.0, 10.0, 10.0)

            periods_data = {
                "am": 80.0,
                "af": 95.0,
                "pm": 90.0,
            }

            for p, base_val in periods_data.items():
                data = np.full((20, 20), base_val, dtype=np.float32)
                # Add offset to cell (0, 0)
                data[:10, :10] += 5.0

                fname = f"predicted_temperature_surface_{p}-whole.tif"
                with rasterio.open(
                    tmp_path / fname,
                    "w",
                    driver="GTiff",
                    height=20,
                    width=20,
                    count=1,
                    dtype="float32",
                    crs="EPSG:32618",
                    transform=transform,
                ) as dst:
                    dst.write(data, 1)

            updated = compute_temperature_zonal_means(self.grid_gdf, maps_dir=tmp_path)

            self.assertIn("temp_am", updated.columns)
            self.assertIn("temp_af", updated.columns)
            self.assertIn("temp_pm", updated.columns)

            # Cell 1 (row 0, col 0) had base + 5.0
            cell_0_0 = updated[updated["id"] == 1].iloc[0]
            self.assertAlmostEqual(cell_0_0["temp_am"], 85.0, places=1)
            self.assertAlmostEqual(cell_0_0["temp_af"], 100.0, places=1)
            self.assertAlmostEqual(cell_0_0["temp_pm"], 95.0, places=1)

            # Cell 2 (row 0, col 1) had base
            cell_0_1 = updated[updated["id"] == 2].iloc[0]
            self.assertAlmostEqual(cell_0_1["temp_am"], 80.0, places=1)
            self.assertAlmostEqual(cell_0_1["temp_af"], 95.0, places=1)
            self.assertAlmostEqual(cell_0_1["temp_pm"], 90.0, places=1)


if __name__ == "__main__":
    unittest.main()

