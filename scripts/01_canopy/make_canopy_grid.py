#!/usr/bin/env python3
"""
make_canopy_grid.py - Main driver for aggregating tree canopy onto the grid.

Computes total tree canopy area and percentage per grid polygon using
high-performance GDAL rasterization and block-windowed NumPy aggregation.
"""

import sys
from pathlib import Path

def get_project_root() -> Path:
    """Locate repository root by searching upward for input_data and uhi directories."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "input_data").is_dir() and (parent / "uhi").is_dir():
            return parent
    return p.parent

PROJECT_ROOT = get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure uhi package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import numpy as np
import pyogrio

import uhi
from uhi.canopy import (
    CANOPY_SOURCES,
    GridSpec,
    create_mask_raster,
    burn_vector_layer,
    aggregate_mask,
    attach_canopy_to_grid,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("canopy_grid")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute tree canopy area and percentage per grid feature."
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=Path("input_data/auxilliary/grid-projection.gpkg"),
        help="Path to grid GeoPackage (default: input_data/auxilliary/grid-projection.gpkg)",
    )
    parser.add_argument(
        "--study-area",
        type=Path,
        default=Path("input_data/county_boundaries/novauhi_counties.gpkg"),
        help="Path to study area boundaries GeoPackage",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output/canopy/grid-canopy.gpkg"),
        help="Path to output GeoPackage (default: output/canopy/grid-canopy.gpkg)",
    )
    parser.add_argument(
        "--res",
        type=float,
        default=1.0,
        help="Rasterization resolution in meters (default: 1.0)",
    )
    parser.add_argument(
        "--reuse-mask",
        action="store_true",
        help="Reuse existing mask GeoTIFF if present in output/canopy",
    )
    parser.add_argument(
        "--keep-mask",
        action="store_true",
        default=True,
        help="Keep the intermediate 1m canopy mask GeoTIFF",
    )

    args = parser.parse_args()

    start_time = time.time()
    logger.info("Reading grid from %s ...", args.grid)
    grid_gdf = pyogrio.read_dataframe(args.grid)
    logger.info("Loaded %d grid features. Deriving GridSpec...", len(grid_gdf))
    spec = GridSpec.from_grid(grid_gdf)
    logger.info(
        "GridSpec: origin=(%.2f, %.2f), cell=%.1fm, shape=%d rows x %d cols",
        spec.x0,
        spec.y0,
        spec.cell_size,
        spec.nrows,
        spec.ncols,
    )

    mask_raster = args.output.parent / f"canopy_mask_{int(args.res)}m.tif"

    if args.reuse_mask and mask_raster.is_file():
        logger.info("Reusing existing canopy mask: %s", mask_raster)
    else:
        logger.info("Initializing mask raster: %s ...", mask_raster)
        create_mask_raster(mask_raster, spec, res=args.res)

        # 1. Burn canopy layers into Band 1
        for name, shp_path, where_clause in CANOPY_SOURCES:
            p = Path(shp_path)
            if not p.is_file():
                logger.error("Canopy shapefile not found: %s", p)
                return 1
            t0 = time.time()
            logger.info("Rasterizing canopy source [%s] (%s) into Band 1 ...", name, p.name)
            burn_vector_layer(
                raster_path=mask_raster,
                vector_path=p,
                band=1,
                where=where_clause,
            )
            logger.info("Completed %s in %.1f s", name, time.time() - t0)

        # 2. Burn study area into Band 2
        if args.study_area.is_file():
            t0 = time.time()
            logger.info("Rasterizing study area [%s] into Band 2 ...", args.study_area.name)
            burn_vector_layer(
                raster_path=mask_raster,
                vector_path=args.study_area,
                band=2,
            )
            logger.info("Completed study area rasterization in %.1f s", time.time() - t0)
        else:
            logger.warning("Study area file %s not found. Proceeding without coverage mask.", args.study_area)

    # 3. Block-aggregate mask values per grid cell
    t_agg = time.time()
    logger.info("Aggregating 100x100 pixel blocks per grid cell...")
    canopy_px, covered_px = aggregate_mask(mask_raster, spec, res=args.res, strip_rows=10)
    logger.info("Aggregation completed in %.1f s", time.time() - t_agg)

    # 4. Attach attributes
    logger.info("Attaching attributes to grid...")
    out_gdf = attach_canopy_to_grid(grid_gdf, canopy_px, covered_px, res=args.res)

    # 5. Save output GeoPackage
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Writing output to %s ...", args.output)
    pyogrio.write_dataframe(out_gdf, args.output, driver="GPKG")

    total_time = time.time() - start_time
    valid_pct = out_gdf["canopy_pct"].dropna()

    print("\n" + "=" * 65)
    print("TREE CANOPY AGGREGATION COMPLETED SUCCESSFULLY")
    print("=" * 65)
    print(f"Total processing time:        {total_time:.1f} s ({total_time/60:.2f} min)")
    print(f"Total grid cells:             {len(out_gdf):,}")
    print(f"Cells inside study area:      {(out_gdf['covered_m2'] > 0).sum():,} ({(out_gdf['covered_m2'] > 0).mean()*100:.1f}%)")
    print(f"Cells outside study area:     {(out_gdf['covered_m2'] == 0).sum():,} (canopy_pct set to NULL)")
    print(f"Canopy % (valid cells):       mean = {valid_pct.mean():.1f}%, median = {valid_pct.median():.1f}%")
    print(f"                              p10 = {valid_pct.quantile(0.10):.1f}%, p90 = {valid_pct.quantile(0.90):.1f}%")
    print(f"Total canopy area:            {out_gdf['canopy_m2'].sum() / 1e6:.2f} km²")
    print(f"Output GeoPackage:            {args.output.resolve()}")
    print("=" * 65 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

