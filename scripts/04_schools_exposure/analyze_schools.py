"""
School Microclimate Analysis & Figure Generation Pipeline
=========================================================
Runs 500m buffer extractions and generates publication-grade figures:
1. Hottest vs. Coolest school temperatures for Morning (AM), Afternoon (AF), and Evening (PM).
2. Tree canopy cover (%) vs. temperature anomaly relationship across diurnal periods.

Usage:
------
python scripts/04_schools_exposure/analyze_schools.py
python scripts/04_schools_exposure/analyze_schools.py --buffer 500 --figures-dir output/figures/schools
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
import geopandas as gpd

import uhi  # Configures GDAL/PROJ environment variables
from uhi.school_analysis import (
    compute_school_buffer_metrics,
    plot_hottest_to_coldest_schools,
    plot_school_canopy_vs_anomaly,
    DEFAULT_SCHOOL_LOCS,
    DEFAULT_BUFFERS_GPKG,
    DEFAULT_CANOPY_MASK,
    DEFAULT_FIGURES_DIR,
    DEFAULT_RASTERS,
    PERIOD_CONFIG,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("analyze_schools")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute 500m school buffer microclimate metrics and generate figures."
    )
    parser.add_argument(
        "--schools",
        type=Path,
        default=DEFAULT_SCHOOL_LOCS,
        help="Path to input school points GeoPackage (default: output/locations/school_locs.gpkg).",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=500.0,
        help="Buffer distance in meters (default: 500.0).",
    )
    parser.add_argument(
        "--output-buffers",
        type=Path,
        default=DEFAULT_BUFFERS_GPKG,
        help="Path to output buffered polygons GeoPackage (default: output/locations/school_buffers_500m.gpkg).",
    )
    parser.add_argument(
        "--canopy-mask",
        type=Path,
        default=DEFAULT_CANOPY_MASK,
        help="Path to 1m canopy mask GeoTIFF (default: output/canopy/canopy_mask_1m.tif).",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=DEFAULT_FIGURES_DIR,
        help="Directory to save output figures (default: output/figures/schools).",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip extraction and use existing buffered GeoPackage if available.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("SCHOOL BUFFER MICROCLIMATE & CANOPY ANALYSIS PIPELINE")
    logger.info("=" * 70)

    # 1. Extraction or loading
    if args.skip_extraction and args.output_buffers.is_file():
        logger.info("Skipping extraction. Loading existing buffers from %s ...", args.output_buffers)
        buffers_gdf = gpd.read_file(args.output_buffers, layer="school_buffers")
    else:
        logger.info("Running 500m buffer extraction on %s ...", args.schools)
        buffers_gdf = compute_school_buffer_metrics(
            schools_path=args.schools,
            buffer_distance=args.buffer,
            rasters=DEFAULT_RASTERS,
            canopy_raster=args.canopy_mask,
            output_gpkg=args.output_buffers,
            update_points_gpkg=args.schools,
        )

    # Ensure secondary root copy is also up-to-date
    root_locs = Path("school_locs.gpkg")
    if root_locs.is_file():
        logger.info("Updating root school_locs.gpkg copy with extracted metrics...")
        root_pts = gpd.read_file(root_locs)
        for c in ["temp_med_am", "temp_med_af", "temp_med_pm", "anom_med_am", "anom_med_af", "anom_med_pm", "canopy_pct"]:
            if c in buffers_gdf.columns:
                root_pts[c] = buffers_gdf[c].values
        root_pts.to_file(root_locs, layer="school_locs", driver="GPKG")

    args.figures_dir.mkdir(parents=True, exist_ok=True)

    # 2. Generate Hottest to Coldest Figures (One per collection time)
    logger.info("-" * 70)
    logger.info("GENERATING HOTTEST TO COLDEST SCHOOL TEMPERATURE FIGURES")
    logger.info("-" * 70)

    generated_figures = []
    for period in ["am", "af", "pm"]:
        out_fig_path = args.figures_dir / f"school_temps_hottest_to_coldest_{period}.png"
        fig = plot_hottest_to_coldest_schools(
            buffers_gdf,
            period=period,
            output_path=out_fig_path,
            n_top=10,
        )
        generated_figures.append(out_fig_path)
        logger.info("Generated %s: %s", period.upper(), out_fig_path)

    # 3. Generate Canopy vs. Temperature Anomaly Figure
    logger.info("-" * 70)
    logger.info("GENERATING CANOPY VS. TEMPERATURE ANOMALY FIGURE")
    logger.info("-" * 70)

    out_scatter_path = args.figures_dir / "school_canopy_vs_temperature_anomaly.png"
    fig_scatter = plot_school_canopy_vs_anomaly(
        buffers_gdf,
        output_path=out_scatter_path,
    )
    generated_figures.append(out_scatter_path)
    logger.info("Generated scatter plot: %s", out_scatter_path)

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("SCHOOL ANALYSIS PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("Total processing time: %.2f s", elapsed)
    logger.info("Output GeoPackage: %s", args.output_buffers)
    logger.info("Generated %d presentation figures in %s:", len(generated_figures), args.figures_dir)
    for fig_path in generated_figures:
        size_mb = fig_path.stat().st_size / (1024 * 1024)
        logger.info("  * %-45s (%.2f MB)", fig_path.name, size_mb)
    logger.info("=" * 70)

    # Print summary table of hottest vs coolest
    print("\n" + "=" * 76)
    print(f"{'Period':<12} | {'Hottest School':<28} | {'Coolest School':<24} | {'Delta T':<9}")
    print("-" * 76)
    for p in ["am", "af", "pm"]:
        col = PERIOD_CONFIG[p]["temp_col"]
        valid = buffers_gdf.dropna(subset=[col]).sort_values(col, ascending=True)
        hottest = valid.iloc[-1]
        coolest = valid.iloc[0]
        dt = hottest[col] - coolest[col]
        hot_str = f"{hottest['school_name'][:20]} ({hottest[col]:.1f} deg F)"
        cool_str = f"{coolest['school_name'][:17]} ({coolest[col]:.1f} deg F)"
        print(f"{PERIOD_CONFIG[p]['label']:<12} | {hot_str:<28} | {cool_str:<24} | {dt:+.2f} F")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
