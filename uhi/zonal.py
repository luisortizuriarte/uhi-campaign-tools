"""
uhi/zonal.py - Zonal statistics computation for grid polygons.

Computes exact zonal mean temperatures for grid polygons using
high-performance raster reprojection with area-weighted average downsampling.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from uhi.canopy import GridSpec

logger = logging.getLogger(__name__)

TEMPERATURE_PERIODS: List[Tuple[str, str, str]] = [
    ("am", "temp_am", "predicted_temperature_surface_am-whole.tif"),
    ("af", "temp_af", "predicted_temperature_surface_af-whole.tif"),
    ("pm", "temp_pm", "predicted_temperature_surface_pm-whole.tif"),
]


def compute_temperature_zonal_means(
    grid_gdf: gpd.GeoDataFrame,
    maps_dir: Union[str, Path] = "input_data/maps",
    spec: Optional[GridSpec] = None,
) -> gpd.GeoDataFrame:
    """
    Compute the zonal mean temperature for each grid cell across morning (AM),
    afternoon (AF), and evening (PM) rasters.

    Parameters
    ----------
    grid_gdf : gpd.GeoDataFrame
        Grid GeoDataFrame with row_index and col_index attributes.
    maps_dir : str or Path
        Directory containing the predicted temperature surface GeoTIFFs.
    spec : GridSpec, optional
        Precomputed GridSpec. If None, derived automatically from grid_gdf.

    Returns
    -------
    gpd.GeoDataFrame
        Updated GeoDataFrame with 'temp_am', 'temp_af', and 'temp_pm' columns.
    """
    maps_path = Path(maps_dir)
    if not maps_path.is_dir():
        raise NotADirectoryError(f"Maps directory not found: {maps_path}")

    if spec is None:
        spec = GridSpec.from_grid(grid_gdf)

    dst_transform = from_origin(spec.x0, spec.y0, spec.cell_size, spec.cell_size)
    dst_crs = f"EPSG:{spec.crs_epsg}"

    r_idx = grid_gdf["row_index"].values.astype(int)
    c_idx = grid_gdf["col_index"].values.astype(int)

    out_gdf = grid_gdf.copy()

    for period, col_name, filename in TEMPERATURE_PERIODS:
        tif_path = maps_path / filename
        if not tif_path.is_file():
            # Try finding any file matching period in filename
            candidates = list(maps_path.glob(f"*{period}*.tif"))
            if candidates:
                tif_path = candidates[0]
            else:
                raise FileNotFoundError(f"Temperature raster for '{period}' not found in {maps_path}")

        logger.info("Computing zonal mean temperature for %s from %s ...", period.upper(), tif_path.name)

        with rasterio.open(tif_path) as src:
            # Downsample to 100m grid using average resampling
            dst_grid = np.full((spec.nrows, spec.ncols), np.nan, dtype=np.float32)

            reproject(
                source=rasterio.band(src, 1),
                destination=dst_grid,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.average,
                dst_nodata=np.nan,
            )

        # Extract values for each grid cell via indices
        cell_temps = dst_grid[r_idx, c_idx]
        out_gdf[col_name] = np.where(np.isfinite(cell_temps), np.round(cell_temps, 2), np.nan)

        valid_count = np.isfinite(cell_temps).sum()
        logger.info(
            "Completed %s: %d / %d cells valid (mean=%.2f °F)",
            col_name,
            valid_count,
            len(out_gdf),
            np.nanmean(cell_temps),
        )

    return out_gdf

