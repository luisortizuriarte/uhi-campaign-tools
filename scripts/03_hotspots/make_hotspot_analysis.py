#!/usr/bin/env python3
"""
make_hotspot_analysis.py - Master driver for spatial hot and cold spot analysis
across Northern Virginia Urban Heat Island campaign.

Executes:
1. Getis-Ord Gi* hotspot detection for AM, AF, and PM on 100m grid with FDR control.
2. Diurnal persistence analysis identifying multi-period heat zones and cool refuges.
3. Canopy cover comparison between persistent hot spots and cold spots.
4. Export of enriched GeoPackage and summary CSVs.
5. Generation of presentation-ready 16:9 figures adhering to GEMINI.md design standards.
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


from pathlib import Path
import logging
import sys
import time

# Ensure uhi is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import pandas as pd
import pyogrio

from uhi.hotspots import (
    analyze_hotspots,
    summarize_hotspots_by_period,
    summarize_persistence,
    summarize_canopy_comparison,
    compare_methods_sensitivity,
)
from uhi.hotspot_plots import (
    plot_map_spots_by_period,
    plot_map_persistence,
    plot_barchart_spot_area_by_period,
    plot_barchart_persistence,
    plot_boxplot_canopy_hot_vs_cold,
    plot_barchart_canopy_by_spot,
    plot_barchart_method_agreement,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hotspot_pipeline")


def main() -> int:
    t_start = time.time()
    logger.info("Starting NOVA Hot & Cold Spot Analysis Pipeline...")

    grid_path = Path("output/canopy/grid-canopy.gpkg")
    boundary_path = Path("input_data/county_boundaries/novauhi_counties.gpkg")
    out_data_dir = Path("output/hotspots")
    out_fig_dir = Path("output/figures/hotspots")

    out_data_dir.mkdir(parents=True, exist_ok=True)
    out_fig_dir.mkdir(parents=True, exist_ok=True)

    if not grid_path.is_file():
        logger.error("Grid dataset not found: %s", grid_path)
        return 1

    # 1. Read input dataset
    logger.info("Loading grid from %s...", grid_path)
    # We read with geometry so we can save back enriched GeoPackage
    gdf = gpd.read_file(grid_path)
    logger.info("Loaded %d grid cells (CRS: %s).", len(gdf), gdf.crs)

    # 2. Run Hot Spot Analysis
    logger.info("Running Getis-Ord Gi* clustering, FDR control, and persistence...")
    enriched = analyze_hotspots(gdf, fdr_threshold=0.05, percentile_threshold=10.0)

    # 3. Generate summary tables
    logger.info("Computing summary tables...")
    period_summary = summarize_hotspots_by_period(enriched)
    persistence_summary = summarize_persistence(enriched)
    canopy_res = summarize_canopy_comparison(enriched)
    canopy_summary = canopy_res["stats_table"]
    sensitivity_summary = compare_methods_sensitivity(enriched)

    # Export CSVs
    period_summary.to_csv(out_data_dir / "summary_by_period.csv", index=False)
    persistence_summary.to_csv(out_data_dir / "persistence_counts.csv", index=False)
    canopy_summary.to_csv(out_data_dir / "canopy_hot_vs_cold.csv", index=False)
    sensitivity_summary.to_csv(out_data_dir / "method_agreement.csv", index=False)
    logger.info("Exported summary CSVs to %s", out_data_dir)

    # 4. Save enriched GeoPackage
    out_gpkg = out_data_dir / "hotspots.gpkg"
    logger.info("Saving enriched GeoPackage to %s...", out_gpkg)
    export_gdf = enriched.copy()
    # Convert bool columns to int for wide GeoPackage compatibility
    for col in export_gdf.columns:
        if export_gdf[col].dtype == bool:
            export_gdf[col] = export_gdf[col].astype(int)

    export_gdf.to_file(out_gpkg, driver="GPKG")
    logger.info("GeoPackage written successfully.")

    # 5. Generate Figures
    logger.info("Generating 16:9 presentation figures...")

    # Figure 1: 3-panel map of hot/cold spots per period
    fig1_path = out_fig_dir / "map_spots_by_period.png"
    plot_map_spots_by_period(enriched, boundary_path=boundary_path, output_path=fig1_path)

    # Figure 2: Diurnal persistence map
    fig2_path = out_fig_dir / "map_persistence.png"
    plot_map_persistence(enriched, boundary_path=boundary_path, output_path=fig2_path)

    # Figure 3: Grouped bar chart of spot area by period
    fig3_path = out_fig_dir / "barchart_spot_area_by_period.png"
    plot_barchart_spot_area_by_period(period_summary, output_path=fig3_path)

    # Figure 4: Persistence tier bar chart
    fig4_path = out_fig_dir / "barchart_persistence.png"
    plot_barchart_persistence(persistence_summary, output_path=fig4_path)

    # Figure 5: Boxplot of canopy cover: Hot All-3 vs Cold All-3
    fig5_path = out_fig_dir / "boxplot_canopy_hot_vs_cold.png"
    plot_boxplot_canopy_hot_vs_cold(enriched, output_path=fig5_path)

    # Figure 6: Grouped bar chart of canopy by spot class per period
    fig6_path = out_fig_dir / "barchart_canopy_by_spot.png"
    plot_barchart_canopy_by_spot(period_summary, output_path=fig6_path)

    # Figure 7: Sensitivity check (Gi* vs Percentile agreement)
    fig7_path = out_fig_dir / "barchart_method_agreement.png"
    plot_barchart_method_agreement(sensitivity_summary, output_path=fig7_path)

    # 6. Print summary report to stdout
    print("\n" + "=" * 78)
    print("NORTHERN VIRGINIA URBAN HEAT ISLAND — HOT & COLD SPOT ANALYSIS SUMMARY")
    print("=" * 78)
    print("\n1. DIURNAL HOT & COLD SPOTS BY COLLECTION TIME:")
    print(period_summary[["period_label", "spot_class", "area_pct", "area_km2", "mean_temp_f", "mean_canopy_pct"]].to_string(index=False))

    print("\n2. DIURNAL PERSISTENCE ACROSS ALL 3 PERIODS:")
    print(persistence_summary[["persistence_class", "area_pct", "area_km2", "mean_canopy_pct", "median_canopy_pct"]].to_string(index=False))

    print("\n3. CANOPY COMPARISON (PERSISTENT HOT VS. COLD SPOTS):")
    print(canopy_summary[["group", "area_km2", "mean_canopy_pct", "median_canopy_pct", "iqr_canopy_pct"]].to_string(index=False))
    print(f"\nMann-Whitney U Test: p = {canopy_res['p_value']:.2e}, Rank-Biserial Effect Size = {canopy_res['rank_biserial_effect_size']:.3f}")
    print(f"Canopy Difference: Cold refuges have +{canopy_res['canopy_difference_median']:.1f}% higher median canopy cover than Hot spots.")

    print("\n4. SENSITIVITY CHECK (PERCENTILE EXTREMES CONFIRMED BY GI* CLUSTERING):")
    print(sensitivity_summary[["period_label", "feature", "share_of_percentile_confirmed_by_gi", "jaccard_index"]].to_string(index=False))

    t_elapsed = time.time() - t_start
    print(f"\nAll operations completed successfully in {t_elapsed:.1f} seconds.")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

