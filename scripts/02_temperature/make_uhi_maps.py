#!/usr/bin/env python3
"""
make_uhi_maps.py - Main driver for generating presentation-ready 16:9 UHI maps.

Loads the urban heat island rasters from input_data/maps, computes spatial statistics
and anomalies, and produces individual and panel comparison figures in 16:9 format.
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
from pathlib import Path

# Ensure uhi package is importable from current working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/script runs
import matplotlib.pyplot as plt

import uhi
from uhi.io import load_uhi_rasters, load_uhi_raster, UHIRaster, PERIOD_ORDER
from uhi.plotting import (
    plot_single_map,
    plot_panel,
    compute_shared_anomaly_limit,
    DEFAULT_DPI,
)
from uhi.variables import get_variable_spec, resolve_clipped_rasters

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("uhi_generator")


def print_summary_table(rasters: list[UHIRaster], shared_lim: float) -> None:
    """Print an ASCII summary table of raster dimensions and temperature stats."""
    header = (
        f"{'Period':<8} | {'Filename':<38} | {'Dims (R×C)':<12} | "
        f"{'Min (°F)':<8} | {'P2 (°F)':<8} | {'Mean (°F)':<9} | {'P98 (°F)':<8} | {'Max (°F)':<8}"
    )
    sep = "-" * len(header)
    print("\n" + sep)
    print("NOVA Heat Watch Campaign — Raster Summary Statistics")
    print(sep)
    print(header)
    print(sep)
    for r in rasters:
        s = r.summary()
        fname = r.source_path.name if r.source_path else "unknown"
        dims = f"{r.data.shape[0]}×{r.data.shape[1]}"
        print(
            f"{r.period.upper():<8} | {fname:<38} | {dims:<12} | "
            f"{s['min']:<8.2f} | {s['p2']:<8.2f} | {s['mean']:<9.2f} | {s['p98']:<8.2f} | {s['max']:<8.2f}"
        )
    print(sep)
    print(f"Shared symmetric anomaly scale limit: ±{shared_lim:.1f} °F")
    print(sep + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate 16:9 presentation maps for NOVA Urban Heat Island campaign."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("input_data/maps"),
        help="Directory containing the input GeoTIFF rasters (default: input_data/maps)",
    )
    parser.add_argument(
        "--boundary",
        "-b",
        type=Path,
        default=Path("input_data/county_boundaries/novauhi_counties.gpkg"),
        help="Region of interest boundary file to clip to (default: input_data/county_boundaries/novauhi_counties.gpkg)",
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Do not clip rasters to the region of interest boundary",
    )
    parser.add_argument(
        "--variable",
        choices=["temperature", "heat_index"],
        default="temperature",
        help="Target climatic variable (default: temperature)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Directory to save generated figures (default derived from --variable)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Resolution for generated figures (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--no-basemap",
        action="store_true",
        help="Disable CartoDB Positron basemap tiles (offline mode)",
    )

    args = parser.parse_args()
    var_spec = get_variable_spec(args.variable)
    output_base = args.output if args.output is not None else var_spec.figures_dir

    boundary = None if args.no_clip else args.boundary
    if boundary and not boundary.is_file():
        logger.warning("Boundary file %s not found. Proceeding without boundary clipping.", boundary)
        boundary = None

    if args.input == Path("input_data/maps") and not args.no_clip:
        logger.info("Resolving boundary-clipped %s rasters...", var_spec.display_name.lower())
        clipped_paths = resolve_clipped_rasters(var_spec, maps_dir=args.input, boundary_path=boundary)
        rasters = [load_uhi_raster(clipped_paths[p], boundary=None) for p in PERIOD_ORDER]
    elif args.input == Path("input_data/maps"):
        rasters = [
            load_uhi_raster(args.input / var_spec.input_rasters[p], boundary=None)
            for p in PERIOD_ORDER
        ]
    else:
        logger.info("Loading rasters from %s (boundary clipping: %s)...", args.input, bool(boundary))
        try:
            rasters = load_uhi_rasters(args.input, pattern=var_spec.raster_glob, boundary=boundary)
        except Exception:
            try:
                rasters = load_uhi_rasters(args.input, boundary=boundary)
            except Exception as exc:
                logger.error("Failed to load rasters: %s", exc)
                return 1

    shared_anomaly_limit = compute_shared_anomaly_limit(rasters)
    print_summary_table(rasters, shared_anomaly_limit)

    add_basemap = not args.no_basemap
    temp_dir = output_base / var_spec.value_subdir
    anom_dir = output_base / "anomaly"
    panel_dir = output_base / "panels"

    generated_files: list[Path] = []

    # 1. Generate individual value maps (3 figures)
    logger.info("Generating individual %s maps (colormap: YlOrRd)...", var_spec.short_name.lower())
    for r in rasters:
        out_file = temp_dir / f"{var_spec.value_file_prefix}_{r.period}.png"
        fig, _ = plot_single_map(
            raster=r,
            kind="temperature",
            add_basemap=add_basemap,
            output_path=out_file,
            dpi=args.dpi,
            variable=var_spec.key,
        )
        plt.close(fig)
        generated_files.append(out_file)

    # 2. Generate individual anomaly maps (3 figures)
    logger.info("Generating individual %s anomaly maps (colormap: Spectral_r)...", var_spec.short_name.lower())
    for r in rasters:
        out_file = anom_dir / f"{var_spec.anomaly_file_prefix}_{r.period}.png"
        fig, _ = plot_single_map(
            raster=r,
            kind="anomaly",
            anomaly_limit=shared_anomaly_limit,
            add_basemap=add_basemap,
            output_path=out_file,
            dpi=args.dpi,
            variable=var_spec.key,
        )
        plt.close(fig)
        generated_files.append(out_file)

    # 3. Generate 3-panel comparison figures (2 figures)
    logger.info("Generating 3-panel %s progression figure...", var_spec.short_name.lower())
    temp_panel_file = panel_dir / f"{var_spec.value_file_prefix}_panel.png"
    fig, _ = plot_panel(
        rasters=rasters,
        kind="temperature",
        add_basemap=add_basemap,
        output_path=temp_panel_file,
        dpi=args.dpi,
        variable=var_spec.key,
    )
    plt.close(fig)
    generated_files.append(temp_panel_file)

    logger.info("Generating 3-panel %s anomaly progression figure...", var_spec.short_name.lower())
    anom_panel_file = panel_dir / f"{var_spec.anomaly_file_prefix}_panel.png"
    fig, _ = plot_panel(
        rasters=rasters,
        kind="anomaly",
        anomaly_limit=shared_anomaly_limit,
        add_basemap=add_basemap,
        output_path=anom_panel_file,
        dpi=args.dpi,
        variable=var_spec.key,
    )
    plt.close(fig)
    generated_files.append(anom_panel_file)

    print("\n" + "=" * 60)
    print("SUCCESS: Generated 8 presentation-ready figures in 16:9 format:")
    print("=" * 60)
    for p in generated_files:
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"  • {p.as_posix():<52} ({size_mb:.2f} MB)")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

