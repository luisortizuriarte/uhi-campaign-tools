#!/usr/bin/env python3
"""
make_canopy_map.py - Generate presentation-grade 16:9 Tree Canopy maps.

Produces:
1. High-resolution continuous gradient Tree Canopy map (output/figures/canopy/map_tree_canopy.png).
2. Discrete 5-tier quintile Tree Canopy map (output/figures/canopy/map_tree_canopy_discrete.png).
3. Updates the overview map (output/canopy/canopy_overview.png) to standard 16:9 presentation style.
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
from pathlib import Path
import sys

# Ensure uhi package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from uhi.canopy_plots import plot_tree_canopy_map, DEFAULT_DPI

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("canopy_mapper")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate presentation-ready 16:9 Tree Canopy maps for NOVA Heat Watch campaign."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("output/canopy/grid-canopy.gpkg"),
        help="Path to grid GeoPackage with canopy_pct (default: output/canopy/grid-canopy.gpkg)",
    )
    parser.add_argument(
        "--boundary",
        "-b",
        type=Path,
        default=Path("input_data/county_boundaries/novauhi_counties.gpkg"),
        help="Path to study area boundaries GeoPackage",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("output/figures/canopy"),
        help="Directory to save figures (default: output/figures/canopy)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["continuous", "discrete", "both"],
        default="both",
        help="Map visualization mode (default: both)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Figure resolution in DPI (default: {DEFAULT_DPI})",
    )

    args = parser.parse_args()

    if not args.input.is_file():
        logger.error("Canopy grid dataset not found: %s", args.input)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    overview_path = Path("output/canopy/canopy_overview.png")
    overview_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Tree Canopy Map generation (Mode: %s)...", args.mode)

    if args.mode in ("continuous", "both"):
        cont_path = args.output_dir / "map_tree_canopy.png"
        logger.info("Generating continuous gradient map -> %s", cont_path)
        plot_tree_canopy_map(
            grid_data=args.input,
            boundary_path=args.boundary,
            output_path=cont_path,
            mode="continuous",
            dpi=args.dpi,
        )

        # Also update the canonical overview map in output/canopy/
        logger.info("Updating canopy overview map -> %s", overview_path)
        plot_tree_canopy_map(
            grid_data=args.input,
            boundary_path=args.boundary,
            output_path=overview_path,
            mode="continuous",
            dpi=args.dpi,
        )

    if args.mode in ("discrete", "both"):
        disc_path = args.output_dir / "map_tree_canopy_discrete.png"
        logger.info("Generating discrete 5-tier quintile map -> %s", disc_path)
        plot_tree_canopy_map(
            grid_data=args.input,
            boundary_path=args.boundary,
            output_path=disc_path,
            mode="discrete",
            dpi=args.dpi,
        )

    logger.info("All Tree Canopy presentation maps generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

