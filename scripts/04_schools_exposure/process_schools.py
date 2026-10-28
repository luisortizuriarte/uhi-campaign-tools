"""
Process School Locations Pipeline Script
========================================
Combines school locations from Alexandria, Arlington, and Fairfax counties:
- Converts polygon building footprints from Alexandria and Arlington into centroids.
- Preserves Fairfax point coordinates.
- Reprojects all features to project CRS (EPSG:32618).
- Saves output to a single GeoPackage named 'school_locs.gpkg'.

Usage:
------
python process_schools.py
python process_schools.py --output output/locations/school_locs.gpkg
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

import uhi  # Configures GDAL/PROJ environment variables
from uhi.locations import (
    combine_school_locations,
    DEFAULT_ALX_PATH,
    DEFAULT_ARL_PATH,
    DEFAULT_FFX_PATH,
    DEFAULT_OUTPUT_GPKG,
    DEFAULT_CRS,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("process_schools")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Combine school datasets into a unified GeoPackage layer of points."
    )
    parser.add_argument(
        "--alx",
        type=Path,
        default=DEFAULT_ALX_PATH,
        help="Path to Alexandria school boundary shapefile.",
    )
    parser.add_argument(
        "--arl",
        type=Path,
        default=DEFAULT_ARL_PATH,
        help="Path to Arlington school building polygons shapefile.",
    )
    parser.add_argument(
        "--ffx",
        type=Path,
        default=DEFAULT_FFX_PATH,
        help="Path to Fairfax school facilities shapefile.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_GPKG,
        help="Path to primary output GeoPackage (default: output/locations/school_locs.gpkg).",
    )
    parser.add_argument(
        "--secondary-output",
        type=Path,
        default=Path("school_locs.gpkg"),
        help="Path to secondary output GeoPackage copy (default: school_locs.gpkg in root).",
    )
    parser.add_argument(
        "--layer",
        type=str,
        default="school_locs",
        help="Name of the layer in the GeoPackage (default: school_locs).",
    )
    parser.add_argument(
        "--crs",
        type=str,
        default=DEFAULT_CRS,
        help="Target coordinate reference system (default: EPSG:32618).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    logger.info("=" * 65)
    logger.info("PROCESSING AND COMBINING SCHOOL LOCATIONS")
    logger.info("=" * 65)

    try:
        combined_gdf = combine_school_locations(
            alx_path=args.alx,
            arl_path=args.arl,
            ffx_path=args.ffx,
            target_crs=args.crs,
            output_gpkg=args.output,
            layer_name=args.layer,
            secondary_output=args.secondary_output,
        )
    except Exception as e:
        logger.error("Failed to process school locations: %s", e, exc_info=True)
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info("=" * 65)
    logger.info("SCHOOL LOCATIONS PROCESSING COMPLETED SUCCESSFULLY")
    logger.info("Total processing time: %.2f s", elapsed)
    logger.info("Total schools processed: %d", len(combined_gdf))
    logger.info("Breakdown by jurisdiction:")
    for juris, count in combined_gdf["jurisdiction"].value_counts().items():
        logger.info("  * %-12s: %d points", juris, count)
    logger.info("Outputs created:")
    if args.output and Path(args.output).is_file():
        size_mb = Path(args.output).stat().st_size / (1024 * 1024)
        logger.info("  * %s (%.2f MB)", args.output, size_mb)
    if args.secondary_output and Path(args.secondary_output).is_file():
        size_mb = Path(args.secondary_output).stat().st_size / (1024 * 1024)
        logger.info("  * %s (%.2f MB)", args.secondary_output, size_mb)
    logger.info("=" * 65)


if __name__ == "__main__":
    main()

