"""Unit tests for the NOVA UHI mapping package."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

import uhi
from uhi.io import (
    UHIRaster,
    extract_period,
    load_uhi_raster,
    load_uhi_rasters,
)
from uhi.plotting import (
    SLIDE_FIGSIZE,
    compute_temperature_limits,
    compute_shared_anomaly_limit,
    plot_single_map,
    plot_panel,
)
import matplotlib.pyplot as plt


class TestUHIIO(unittest.TestCase):
    """Test suite for UHI raster I/O and data models."""

    def test_extract_period(self):
        self.assertEqual(extract_period("predicted_temperature_surface_am-whole.tif"), "am")
        self.assertEqual(extract_period("predicted_temperature_surface_af-whole.tif"), "af")
        self.assertEqual(extract_period("predicted_temperature_surface_pm-whole.tif"), "pm")
        self.assertEqual(extract_period("uhi_AM_map.tif"), "am")
        self.assertEqual(extract_period("heat_AF_2021.tif"), "af")
        self.assertEqual(extract_period("morning_clipped.tif"), "am")
        self.assertEqual(extract_period("afternoon_clipped.tif"), "af")
        self.assertEqual(extract_period("evening_clipped.tif"), "pm")

        with self.assertRaises(ValueError):
            extract_period("random_surface_file.tif")

    def test_uhiraster_properties(self):
        # 10x10 array with known mean
        data = np.arange(100, dtype=np.float32).reshape(10, 10)
        data[0, 0] = np.nan  # include a NaN

        raster = UHIRaster(
            period="am",
            label="Morning (AM)",
            data=data,
            extent=(280000.0, 320000.0, 4280000.0, 4320000.0),
            crs=rasterio.crs.CRS.from_epsg(32618),
            transform=from_origin(280000.0, 4320000.0, 4000.0, 4000.0),
        )

        expected_mean = float(np.nanmean(data))
        self.assertAlmostEqual(raster.spatial_mean, expected_mean, places=4)

        anomaly = raster.anomaly
        self.assertEqual(anomaly.shape, data.shape)
        self.assertTrue(np.isnan(anomaly[0, 0]))
        # Anomaly spatial mean should be ~0
        self.assertAlmostEqual(float(np.nanmean(anomaly)), 0.0, places=4)

        stats = raster.summary()
        self.assertIn("min", stats)
        self.assertIn("mean", stats)
        self.assertIn("max", stats)
        self.assertAlmostEqual(stats["mean"], expected_mean, places=4)
        self.assertEqual(stats["valid_pct"], 99.0)

    def test_load_synthetic_geotiff(self):
        # Create a small temporary GeoTIFF
        with tempfile.TemporaryDirectory() as tmpdir:
            tif_path = Path(tmpdir) / "predicted_temperature_surface_am-test.tif"
            transform = from_origin(300000.0, 4300000.0, 10.0, 10.0)
            data = np.ones((20, 20), dtype=np.float32) * 82.5

            with rasterio.open(
                tif_path,
                "w",
                driver="GTiff",
                height=20,
                width=20,
                count=1,
                dtype="float32",
                crs="EPSG:32618",
                transform=transform,
                nodata=-9999.0,
            ) as dst:
                dst.write(data, 1)

            raster = load_uhi_raster(tif_path)
            self.assertEqual(raster.period, "am")
            self.assertEqual(raster.label, "Morning (AM)")
            self.assertEqual(raster.data.shape, (20, 20))
            self.assertAlmostEqual(raster.spatial_mean, 82.5, places=3)
            self.assertEqual(raster.crs.to_epsg(), 32618)


class TestUHIPlotting(unittest.TestCase):
    """Test suite for plotting and visualization routines."""

    def setUp(self):
        # Create synthetic rasters for AM, AF, PM
        self.rasters = []
        for period, base_temp in [("am", 80.0), ("af", 95.0), ("pm", 92.0)]:
            np.random.seed(42)
            noise = np.random.normal(0, 2.0, (30, 30)).astype(np.float32)
            data = base_temp + noise
            r = UHIRaster(
                period=period,
                label=uhi.io.PERIODS[period],
                data=data,
                extent=(284000.0, 324000.0, 4280000.0, 4320000.0),
                crs=rasterio.crs.CRS.from_epsg(32618),
                transform=from_origin(284000.0, 4320000.0, 10.0, 10.0),
            )
            self.rasters.append(r)

    def test_compute_anomaly_limit(self):
        lim = compute_shared_anomaly_limit(self.rasters, percentile=98.0)
        self.assertGreater(lim, 0.0)
        # Should be a multiple of 0.5
        self.assertEqual(lim * 2, int(lim * 2))

    def test_plot_single_map_temperature(self):
        fig, ax = plot_single_map(
            self.rasters[0],
            kind="temperature",
            add_basemap=False,
            dpi=72,
        )
        # Confirm 16:9 aspect ratio of the figure canvas
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        for spine in ax.spines.values():
            self.assertFalse(spine.get_visible())
        plt.close(fig)

    def test_plot_single_map_anomaly(self):
        fig, ax = plot_single_map(
            self.rasters[0],
            kind="anomaly",
            anomaly_limit=4.5,
            add_basemap=False,
            dpi=72,
        )
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        for spine in ax.spines.values():
            self.assertFalse(spine.get_visible())
        plt.close(fig)

    def test_plot_panel(self):
        fig, axes = plot_panel(
            self.rasters,
            kind="temperature",
            add_basemap=False,
            dpi=72,
        )
        self.assertEqual(len(axes), 3)
        self.assertAlmostEqual(fig.get_figwidth(), SLIDE_FIGSIZE[0], places=2)
        self.assertAlmostEqual(fig.get_figheight(), SLIDE_FIGSIZE[1], places=2)
        for ax in axes:
            for spine in ax.spines.values():
                self.assertFalse(spine.get_visible())
        plt.close(fig)

    def test_clip_raster(self):
        from shapely.geometry import box
        import geopandas as gpd
        # Synthetic raster spans x: [284000, 284300], y: [4319700, 4320000]
        # Create a boundary box covering only the western half: x in [284000, 284150]
        b = box(284000.0, 4319700.0, 284150.0, 4320000.0)
        gdf = gpd.GeoDataFrame(geometry=[b], crs="EPSG:32618")
        clipped = self.rasters[0].clip(gdf)
        self.assertEqual(clipped.data.shape, self.rasters[0].data.shape)
        # Check that NaN count increased due to clipping
        self.assertGreater(np.isnan(clipped.data).sum(), np.isnan(self.rasters[0].data).sum())


if __name__ == "__main__":
    unittest.main()

