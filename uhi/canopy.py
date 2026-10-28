"""
uhi/canopy.py - Tree canopy processing and grid aggregation.
Uses GDAL rasterization for efficient, out-of-core polygon-to-grid aggregation.
"""

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
from rasterio.transform import from_origin

logger = logging.getLogger(__name__)

CANOPY_SOURCES: List[Tuple[str, str, Optional[str]]] = [
    (
        "fairfax_2021",
        "input_data/tree canopy/ffx_Tree_Canopy_2021_3921158144386413222/Tree_Canopy_2021.shp",
        None,
    ),
    (
        "arlington_2023",
        "input_data/tree canopy/arl_Tree_Canopy_2023/Tree_Canopy_2023.shp",
        None,
    ),
    (
        "alexandria_2013",
        "input_data/tree canopy/alx_Canopy_2013-shp/Canopy_2013.shp",
        None,
    ),
]


@dataclass
class GridSpec:
    """Defines spatial bounding box and raster grid specifications derived from vector grid."""
    x0: float
    y0: float
    cell_size: float
    ncols: int
    nrows: int
    crs_epsg: int = 32618

    @classmethod
    def from_grid(cls, grid_gdf: gpd.GeoDataFrame) -> "GridSpec":
        """Validate grid uniformity and extract GridSpec."""
        x0 = float(grid_gdf["left"].min())
        y0 = float(grid_gdf["top"].max())

        # Determine cell size from bounding columns
        dx = float((grid_gdf["right"] - grid_gdf["left"]).median())
        dy = float((grid_gdf["top"] - grid_gdf["bottom"]).median())
        if not np.isclose(dx, dy, atol=1e-3):
            raise ValueError(f"Non-square grid cells detected: dx={dx}, dy={dy}")
        cell_size = dx

        col_min = int(grid_gdf["col_index"].min())
        col_max = int(grid_gdf["col_index"].max())
        row_min = int(grid_gdf["row_index"].min())
        row_max = int(grid_gdf["row_index"].max())

        ncols = col_max - col_min + 1
        nrows = row_max - row_min + 1

        if len(grid_gdf) != ncols * nrows:
            logger.warning(
                "Grid cell count (%d) differs from full matrix ncols*nrows (%d)",
                len(grid_gdf),
                ncols * nrows,
            )

        return cls(
            x0=x0,
            y0=y0,
            cell_size=cell_size,
            ncols=ncols,
            nrows=nrows,
            crs_epsg=32618,
        )


def get_gdal_bin(exe_name: str) -> str:
    """Locate gdal executable in current python prefix."""
    prefix = Path(sys.prefix)
    candidates = [
        prefix / "Library" / "bin" / f"{exe_name}.exe",
        prefix / "bin" / f"{exe_name}.exe",
        prefix / "Library" / "bin" / exe_name,
        prefix / "bin" / exe_name,
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return exe_name


def create_mask_raster(
    raster_path: Union[str, Path],
    spec: GridSpec,
    res: float = 1.0,
) -> None:
    """
    Initialize an empty 2-band uint8 GeoTIFF aligned with grid:
      Band 1: Canopy mask (0 / 1)
      Band 2: Study Area coverage mask (0 / 1)
    """
    raster_path = Path(raster_path)
    raster_path.parent.mkdir(parents=True, exist_ok=True)

    width = int(round(spec.ncols * spec.cell_size / res))
    height = int(round(spec.nrows * spec.cell_size / res))
    transform = from_origin(spec.x0, spec.y0, res, res)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 2,
        "dtype": "uint8",
        "crs": f"EPSG:{spec.crs_epsg}",
        "transform": transform,
        "nodata": None,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
    }

    logger.info(
        "Creating mask raster: %s (%dx%d px @ %.1fm, 2 bands)...",
        raster_path.name,
        width,
        height,
        res,
    )
    init_w = min(width, 512)
    init_h = min(height, 512)
    with rasterio.open(raster_path, "w", **profile) as dst:
        # Initialize first block with zeros
        dst.write(np.zeros((2, init_h, init_w), dtype=np.uint8), window=rasterio.windows.Window(0, 0, init_w, init_h))


def burn_vector_layer(
    raster_path: Union[str, Path],
    vector_path: Union[str, Path],
    band: int,
    where: Optional[str] = None,
    all_touched: bool = False,
) -> None:
    """
    Burn a vector dataset into a specific band of the GeoTIFF using gdal_rasterize.
    GDAL handles on-the-fly CRS transformation and scanline rasterization in C++.
    """
    gdal_rasterize = get_gdal_bin("gdal_rasterize")
    raster_path_str = str(Path(raster_path).resolve())
    vector_path_str = str(Path(vector_path).resolve())

    cmd = [
        gdal_rasterize,
        "-b",
        str(band),
        "-burn",
        "1",
    ]
    if all_touched:
        cmd.append("-at")
    if where:
        cmd.extend(["-where", where])

    cmd.extend([vector_path_str, raster_path_str])

    # Pass environmental variables for GDAL/PROJ
    env = os.environ.copy()
    prefix = Path(sys.prefix)
    gdal_data = prefix / "Library" / "share" / "gdal"
    proj_lib = prefix / "Library" / "share" / "proj"
    if gdal_data.is_dir():
        env["GDAL_DATA"] = str(gdal_data)
    if proj_lib.is_dir():
        env["PROJ_LIB"] = str(proj_lib)
    env["GDAL_CACHEMAX"] = "2048"

    logger.info("Executing: %s", " ".join(cmd[:6]) + f" ... {Path(vector_path).name} -> band {band}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("gdal_rasterize stderr:\n%s", result.stderr)
        raise RuntimeError(f"gdal_rasterize failed with code {result.returncode}: {result.stderr}")


def aggregate_mask(
    raster_path: Union[str, Path],
    spec: GridSpec,
    res: float = 1.0,
    strip_rows: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read the mask raster in horizontal strips and block-sum 100x100 pixels per cell.

    Returns:
      canopy_px: (nrows, ncols) array of valid canopy pixels inside study area
      covered_px: (nrows, ncols) array of study area pixels inside each cell
    """
    pixels_per_cell = int(round(spec.cell_size / res))
    canopy_px = np.zeros((spec.nrows, spec.ncols), dtype=np.uint32)
    covered_px = np.zeros((spec.nrows, spec.ncols), dtype=np.uint32)

    with rasterio.open(raster_path) as src:
        total_width_px = src.width
        # Process in chunks of grid rows
        for r_start in range(0, spec.nrows, strip_rows):
            r_end = min(r_start + strip_rows, spec.nrows)
            n_rows_chunk = r_end - r_start

            row_px_start = r_start * pixels_per_cell
            row_px_height = n_rows_chunk * pixels_per_cell

            window = rasterio.windows.Window(
                col_off=0,
                row_off=row_px_start,
                width=total_width_px,
                height=row_px_height,
            )

            # Read both bands: shape (2, height_px, width_px)
            data = src.read(window=window)
            b1 = data[0]  # canopy
            b2 = data[1]  # study area

            # Canopy inside study area only
            canopy_mask = (b1 > 0) & (b2 > 0)
            study_mask = (b2 > 0)

            # Reshape to (n_rows_chunk, pixels_per_cell, ncols, pixels_per_cell) and sum
            canopy_sum = canopy_mask.reshape(
                n_rows_chunk, pixels_per_cell, spec.ncols, pixels_per_cell
            ).sum(axis=(1, 3))

            covered_sum = study_mask.reshape(
                n_rows_chunk, pixels_per_cell, spec.ncols, pixels_per_cell
            ).sum(axis=(1, 3))

            canopy_px[r_start:r_end, :] = canopy_sum
            covered_px[r_start:r_end, :] = covered_sum

    return canopy_px, covered_px


def attach_canopy_to_grid(
    grid_gdf: gpd.GeoDataFrame,
    canopy_px: np.ndarray,
    covered_px: np.ndarray,
    res: float = 1.0,
) -> gpd.GeoDataFrame:
    """
    Join aggregated cell metrics back to vector GeoDataFrame based on row_index and col_index.
    """
    pixel_area = res * res  # m^2 per pixel

    r_idx = grid_gdf["row_index"].values.astype(int)
    c_idx = grid_gdf["col_index"].values.astype(int)

    c_vals = canopy_px[r_idx, c_idx].astype(np.float64) * pixel_area
    cov_vals = covered_px[r_idx, c_idx].astype(np.float64) * pixel_area

    # Calculate coverage fraction relative to expected cell area (100x100 = 10,000 m^2)
    nominal_cell_area = 10000.0
    coverage_frac = np.clip(cov_vals / nominal_cell_area, 0.0, 1.0)

    # Calculate canopy percentage: canopy_m2 / covered_m2 * 100
    with np.errstate(divide="ignore", invalid="ignore"):
        canopy_pct = np.where(cov_vals > 0, (c_vals / cov_vals) * 100.0, np.nan)

    out_gdf = grid_gdf.copy()
    out_gdf["canopy_m2"] = np.round(c_vals, 1)
    out_gdf["covered_m2"] = np.round(cov_vals, 1)
    out_gdf["coverage_frac"] = np.round(coverage_frac, 4)
    out_gdf["canopy_pct"] = np.round(canopy_pct, 2)

    return out_gdf
