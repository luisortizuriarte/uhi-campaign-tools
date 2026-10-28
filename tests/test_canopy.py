"""Unit tests for tree canopy rasterization and aggregation routines."""

import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyogrio
from shapely.geometry import Polygon, box

import uhi
from uhi.canopy import (
    GridSpec,
    create_mask_raster,
    burn_vector_layer,
    aggregate_mask,
    attach_canopy_to_grid,
)


class TestCanopyProcessing(unittest.TestCase):
    """Test suite for canopy rasterization and grid aggregation."""

    def setUp(self):
        # Create a small 3x3 synthetic grid of 100m cells
        # Origin (x0=300000, y0=4300000)
        polys = []
        ids, rows, cols = [], [], []
        lefts, tops, rights, bottoms = [], [], [], []

        cell_size = 100.0
        x0, y0 = 300000.0, 4300000.0

        count = 1
        for r in range(3):
            for c in range(3):
                l = x0 + c * cell_size
                t = y0 - r * cell_size
                r_coord = l + cell_size
                b = t - cell_size

                polys.append(box(l, b, r_coord, t))
                ids.append(count)
                rows.append(r)
                cols.append(c)
                lefts.append(l)
                tops.append(t)
                rights.append(r_coord)
                bottoms.append(b)
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

    def test_gridspec_derivation(self):
        spec = GridSpec.from_grid(self.grid_gdf)
        self.assertEqual(spec.ncols, 3)
        self.assertEqual(spec.nrows, 3)
        self.assertEqual(spec.cell_size, 100.0)
        self.assertEqual(spec.x0, 300000.0)
        self.assertEqual(spec.y0, 4300000.0)

    def test_rasterize_and_aggregation_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mask_raster = tmp_path / "test_mask.tif"
            canopy_shp = tmp_path / "test_canopy.shp"
            study_shp = tmp_path / "test_study.shp"

            spec = GridSpec.from_grid(self.grid_gdf)
            create_mask_raster(mask_raster, spec, res=2.0)  # 2m res for quick test

            # Create a 50x50m canopy square in cell (0, 0)
            # Area = 2,500 m^2 -> should be 25% of the 100x100m cell
            canopy_poly = box(300000.0, 4299950.0, 300050.0, 4300000.0)
            canopy_gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[canopy_poly], crs="EPSG:32618")
            pyogrio.write_dataframe(canopy_gdf, canopy_shp)

            # Study area covers first row and second row, but leaves third row outside
            study_poly = box(300000.0, 4299800.0, 300300.0, 4300000.0)
            study_gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[study_poly], crs="EPSG:32618")
            pyogrio.write_dataframe(study_gdf, study_shp)

            # Burn canopy into Band 1
            burn_vector_layer(mask_raster, canopy_shp, band=1)
            # Burn study area into Band 2
            burn_vector_layer(mask_raster, study_shp, band=2)

            canopy_px, covered_px = aggregate_mask(mask_raster, spec, res=2.0)
            result_gdf = attach_canopy_to_grid(self.grid_gdf, canopy_px, covered_px, res=2.0)

            # Cell (0, 0) is id=1
            cell_0_0 = result_gdf[result_gdf["id"] == 1].iloc[0]
            self.assertAlmostEqual(cell_0_0["canopy_m2"], 2500.0, delta=100.0)
            self.assertAlmostEqual(cell_0_0["canopy_pct"], 25.0, delta=1.5)
            self.assertEqual(cell_0_0["coverage_frac"], 1.0)

            # Cell (2, 2) is id=9 (in row 2, outside study area)
            cell_2_2 = result_gdf[result_gdf["id"] == 9].iloc[0]
            self.assertEqual(cell_2_2["covered_m2"], 0.0)
            self.assertEqual(cell_2_2["coverage_frac"], 0.0)
            self.assertTrue(np.isnan(cell_2_2["canopy_pct"]))


if __name__ == "__main__":
    unittest.main()

