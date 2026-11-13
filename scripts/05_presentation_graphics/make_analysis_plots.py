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
from uhi.variables import get_variable_spec

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("analysis_plots")


def generate_plots_for_metric(
    df,
    metric: str,
    out_dir: Path,
    dpi: int,
    variable: str = "temperature",
) -> list[Path]:
    """Generate all scatter, bar, and box plots for a specific metric ('temperature' or 'anomaly')."""
    var_spec = get_variable_spec(variable)
    is_anomaly = (metric == "anomaly")
    col_prefix = "anom" if is_anomaly else "temp"
    file_prefix = "anom" if is_anomaly else ("hi" if var_spec.key == "heat_index" else "temp")
    cols = [f"{col_prefix}_am", f"{col_prefix}_af", f"{col_prefix}_pm"]
    generated: list[Path] = []

    metric_title = (
        f"{var_spec.display_name} Anomaly"
        if is_anomaly
        else f"Absolute {var_spec.display_name}"
    )
    logger.info("--- Generating figures for %s ---", metric_title)

    # 1. Scatter plots
    for col in cols:
        period = col.split("_")[-1]
        fname = out_dir / f"scatter_canopy_{file_prefix}_{period}.png"
        fig, _ = plot_scatter_canopy_temp(
            df, col, output_path=fname, dpi=dpi, variable=var_spec.key
        )
        plt.close(fig)
        generated.append(fname)

    # 2. Grouped bar chart
    grouped_bar_file = out_dir / f"barchart_canopy_quintiles_{file_prefix}_grouped.png"
    fig, _ = plot_grouped_barchart(
        df, cols=cols, output_path=grouped_bar_file, dpi=dpi, variable=var_spec.key
    )
    plt.close(fig)
    generated.append(grouped_bar_file)

    # Individual bar charts
    for col in cols:
        period = col.split("_")[-1]
        fname = out_dir / f"barchart_canopy_quintiles_{file_prefix}_{period}.png"
        fig, _ = plot_single_barchart(
            df, col, output_path=fname, dpi=dpi, variable=var_spec.key
        )
        plt.close(fig)
        generated.append(fname)

    # 3. Grouped box plot
    grouped_box_file = out_dir / f"boxplot_canopy_quintiles_{file_prefix}_grouped.png"
    fig, _ = plot_grouped_boxplot(
        df, cols=cols, output_path=grouped_box_file, dpi=dpi, variable=var_spec.key
    )
    plt.close(fig)
    generated.append(grouped_box_file)

    # Individual box plots
    for col in cols:
        period = col.split("_")[-1]
        fname = out_dir / f"boxplot_canopy_quintiles_{file_prefix}_{period}.png"
        fig, _ = plot_single_boxplot(
            df, col, output_path=fname, dpi=dpi, variable=var_spec.key
        )
        plt.close(fig)
        generated.append(fname)

    return generated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate canopy cover vs temperature/heat index/anomaly charts (scatter, bar, boxplot)."
    )
    parser.add_argument(
        "--variable",
        choices=["temperature", "heat_index"],
        default="temperature",
        help="Target thermal variable ('temperature' or 'heat_index').",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=None,
        help="Path to grid GeoPackage with canopy and thermal data (default resolved from --variable)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Directory to save generated figures (default resolved from --variable)",
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
    var_spec = get_variable_spec(args.variable)
    grid_path = args.grid if args.grid is not None else var_spec.grid_output_gpkg
    out_dir = args.output_dir if args.output_dir is not None else (var_spec.figures_dir / "analysis")

    t0 = time.time()
    logger.info("Loading %s analysis data from %s ...", var_spec.display_name, grid_path)
    df = load_analysis_dataframe(grid_path)
    logger.info("Loaded %d valid records inside study area.", len(df))

    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    metrics_to_run = ["anomaly"] if args.metric == "anomaly" else (
        ["temperature"] if args.metric == "temperature" else ["temperature", "anomaly"]
    )

    for m in metrics_to_run:
        figs = generate_plots_for_metric(df, m, out_dir, args.dpi, variable=var_spec.key)
        generated.extend(figs)

    total_time = time.time() - t0

    print("\n" + "=" * 70)
    print(f"CANOPY VS. {var_spec.display_name.upper()}/ANOMALY ANALYSIS PLOTS GENERATED SUCCESSFULLY")
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
