#!/usr/bin/env python3
"""
make_analysis_plots.py - Generate comparative analysis charts of canopy cover vs temperature/anomaly.

Produces presentation-ready 16:9 figures:
1. Scatter plots with density hexbins and linear regression trendlines (AM, AF, PM).
2. Grouped bar chart across quintiles + 3 individual bar charts with 95% confidence intervals.
3. Grouped box plot across quintiles + 3 individual box plots showing distributions.

Supports generating figures for temperature, anomaly, or both.
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

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

import uhi
from uhi.analysis import (
    DEFAULT_DPI,
    VARIABLE_CONFIG,
    load_analysis_dataframe,
    plot_scatter_canopy_temp,
    plot_grouped_barchart,
    plot_single_barchart,
    plot_grouped_boxplot,
    plot_single_boxplot,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("analysis_plots")


def generate_plots_for_metric(df, metric: str, out_dir: Path, dpi: int) -> list[Path]:
    """Generate all scatter, bar, and box plots for a specific metric ('temperature' or 'anomaly')."""
    is_anomaly = (metric == "anomaly")
    prefix = "anom" if is_anomaly else "temp"
    cols = [f"{prefix}_am", f"{prefix}_af", f"{prefix}_pm"]
    generated: list[Path] = []

    metric_title = "Temperature Anomaly" if is_anomaly else "Absolute Temperature"
    logger.info("--- Generating figures for %s ---", metric_title)

    # 1. Scatter plots
    for col in cols:
        fname = out_dir / f"scatter_canopy_{col}.png"
        fig, _ = plot_scatter_canopy_temp(df, col, output_path=fname, dpi=dpi)
        plt.close(fig)
        generated.append(fname)

    # 2. Grouped bar chart
    grouped_bar_file = out_dir / f"barchart_canopy_quintiles_{prefix}_grouped.png"
    fig, _ = plot_grouped_barchart(df, cols=cols, output_path=grouped_bar_file, dpi=dpi)
    plt.close(fig)
    generated.append(grouped_bar_file)

    # Individual bar charts
    for col in cols:
        fname = out_dir / f"barchart_canopy_quintiles_{col}.png"
        fig, _ = plot_single_barchart(df, col, output_path=fname, dpi=dpi)
        plt.close(fig)
        generated.append(fname)

    # 3. Grouped box plot
    grouped_box_file = out_dir / f"boxplot_canopy_quintiles_{prefix}_grouped.png"
    fig, _ = plot_grouped_boxplot(df, cols=cols, output_path=grouped_box_file, dpi=dpi)
    plt.close(fig)
    generated.append(grouped_box_file)

    # Individual box plots
    for col in cols:
        fname = out_dir / f"boxplot_canopy_quintiles_{col}.png"
        fig, _ = plot_single_boxplot(df, col, output_path=fname, dpi=dpi)
        plt.close(fig)
        generated.append(fname)

    return generated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate canopy cover vs temperature/anomaly charts (scatter, bar, boxplot)."
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=Path("output/canopy/grid-canopy.gpkg"),
        help="Path to grid GeoPackage with canopy and temperature data (default: output/canopy/grid-canopy.gpkg)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("output/figures/analysis"),
        help="Directory to save generated figures (default: output/figures/analysis)",
    )
    parser.add_argument(
        "--metric",
        "-m",
        choices=["anomaly", "temperature", "all"],
        default="all",
        help="Which metric to plot: 'anomaly', 'temperature', or 'all' (default: all)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Resolution for generated figures (default: {DEFAULT_DPI})",
    )

    args = parser.parse_args()

    t0 = time.time()
    logger.info("Loading analysis data from %s ...", args.grid)
    df = load_analysis_dataframe(args.grid)
    logger.info("Loaded %d valid records inside study area.", len(df))

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    metrics_to_run = ["anomaly"] if args.metric == "anomaly" else (
        ["temperature"] if args.metric == "temperature" else ["temperature", "anomaly"]
    )

    for m in metrics_to_run:
        figs = generate_plots_for_metric(df, m, out_dir, args.dpi)
        generated.extend(figs)

    total_time = time.time() - t0

    print("\n" + "=" * 70)
    print("CANOPY VS. TEMPERATURE/ANOMALY ANALYSIS PLOTS GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"Total processing time: {total_time:.2f} s")
    print(f"Generated {len(generated)} presentation figures (16:9 widescreen, {args.dpi} DPI):")
    for p in generated:
        mb = p.stat().st_size / (1024 * 1024)
        print(f"  • {p.name:<48} ({mb:.2f} MB)")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
