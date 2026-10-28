"""
Unit tests for uhi.locations module.
"""

import unittest
from pathlib import Path
import tempfile
import geopandas as gpd
from uhi.locations import (
    load_alx_schools,
    load_arl_schools,
    load_ffx_schools,
    combine_school_locations,
    DEFAULT_ALX_PATH,
    DEFAULT_ARL_PATH,
    DEFAULT_FFX_PATH,
    DEFAULT_CRS,
)


class TestSchoolLocations(unittest.TestCase):
    def test_load_alx_schools(self):
        gdf = load_alx_schools(DEFAULT_ALX_PATH, target_crs=DEFAULT_CRS)
        self.assertEqual(len(gdf), 18)
        self.assertTrue((gdf.geom_type == "Point").all())
        self.assertEqual(gdf.crs.to_string(), DEFAULT_CRS)
        self.assertTrue("school_name" in gdf.columns)
        self.assertTrue("jurisdiction" in gdf.columns)
        self.assertTrue((gdf["jurisdiction"] == "Alexandria").all())
        self.assertTrue((gdf["orig_geom"] == "Polygon").all())

    def test_load_arl_schools(self):
        gdf = load_arl_schools(DEFAULT_ARL_PATH, target_crs=DEFAULT_CRS)
        self.assertEqual(len(gdf), 37)
        self.assertTrue((gdf.geom_type == "Point").all())
        self.assertEqual(gdf.crs.to_string(), DEFAULT_CRS)
        self.assertTrue("school_name" in gdf.columns)
        self.assertTrue("jurisdiction" in gdf.columns)
        self.assertTrue((gdf["jurisdiction"] == "Arlington").all())
        self.assertTrue((gdf["orig_geom"] == "Polygon").all())

    def test_load_ffx_schools(self):
        gdf = load_ffx_schools(DEFAULT_FFX_PATH, target_crs=DEFAULT_CRS)
        self.assertEqual(len(gdf), 206)
        self.assertTrue((gdf.geom_type == "Point").all())
        self.assertEqual(gdf.crs.to_string(), DEFAULT_CRS)
        self.assertTrue("school_name" in gdf.columns)
        self.assertTrue("jurisdiction" in gdf.columns)
        self.assertTrue((gdf["jurisdiction"] == "Fairfax").all())
        self.assertTrue((gdf["orig_geom"] == "Point").all())

    def test_combine_school_locations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_school_locs.gpkg"
            combined = combine_school_locations(
                alx_path=DEFAULT_ALX_PATH,
                arl_path=DEFAULT_ARL_PATH,
                ffx_path=DEFAULT_FFX_PATH,
                target_crs=DEFAULT_CRS,
                output_gpkg=out_file,
                layer_name="school_locs",
                secondary_output=None,
            )
            self.assertEqual(len(combined), 18 + 37 + 206)
            self.assertTrue(out_file.is_file())

            # Read back from GeoPackage
            saved_gdf = gpd.read_file(out_file, layer="school_locs")
            self.assertEqual(len(saved_gdf), 261)
            self.assertEqual(saved_gdf.crs.to_string(), DEFAULT_CRS)
            self.assertTrue((saved_gdf.geom_type == "Point").all())
            self.assertEqual(
                saved_gdf["jurisdiction"].value_counts().to_dict(),
                {"Fairfax": 206, "Arlington": 37, "Alexandria": 18},
            )


if __name__ == "__main__":
    unittest.main()

