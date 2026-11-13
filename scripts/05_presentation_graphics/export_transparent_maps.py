#!/usr/bin/env python3
"""
export_transparent_maps.py - Generate clean, standalone map-only copies of all
project maps with transparent backgrounds at 300 DPI.

Removes:
- Legends and color keys
- Titles, subtitles, and notes
- Colorbars and side interpretation cards
- Coordinate axes, ticks, tick labels, and spines

Sets:
- Figure and axis background to transparent (alpha = 0)
- Resolution to 300 DPI
- Tight bounding box (pad_inches = 0.02)
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
import sys
from pathlib import Path
import logging

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm, ListedColormap
import numpy as np
import pandas as pd
import pyogrio

# Ensure local uhi package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uhi.io import load_uhi_raster
from uhi.plotting import compute_temperature_limits, compute_shared_anomaly_limit, TEMP_CMAP, ANOM_CMAP
from uhi.variables import VariableSpec, get_variable_spec, resolve_clipped_rasters

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("export_transparent_maps")

# Paths
INPUT_DIR = Path("input_data/maps")
BOUNDARY_PATH = Path("input_data/county_boundaries/novauhi_counties.gpkg")
CANOPY_GRID_PATH = Path("output/canopy/grid-canopy.gpkg")

# Color constants matching GEMINI.md
COLOR_BORDER_CANOPY = "#4B5563"
COLOR_BORDER_HOTSPOTS = "#9CA3AF"
COLOR_NS = "#E5E7EB"
COLOR_COLD = "#2980B9"
COLOR_COLD_LIGHT = "#D4E6F1"
COLOR_COLD_MID = "#85C1E9"
COLOR_HOT = "#E74C3C"
COLOR_HOT_LIGHT = "#FADBD8"
COLOR_HOT_MID = "#F1948A"

CONF_COLORS = [
    "#1D4ED8",  # Cold 99%
    "#3B82F6",  # Cold 95%
    "#93C5FD",  # Cold 90%
    "#E5E7EB",  # Not Significant
    "#FCA5A5",  # Hot 90%
    "#EF4444",  # Hot 95%
    "#B91C1C",  # Hot 99%
]


def save_transparent(fig: plt.Figure, primary_path: Path, central_dir: Path, central_name: str) -> None:
    """Save figure with transparent background at 300 DPI to primary and central directories."""
    primary_path.parent.mkdir(parents=True, exist_ok=True)
    central_dir.mkdir(parents=True, exist_ok=True)
    central_path = central_dir / central_name

    fig.patch.set_alpha(0.0)
    fig.savefig(primary_path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(central_path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    logger.info("Saved transparent map: %s (and in %s)", primary_path.name, central_dir.name)


def export_temperature_and_anomaly_maps(var_spec: VariableSpec, output_base: Path, central_dir: Path) -> None:
    """Export single and 3-panel temperature/heat index and anomaly maps."""
    logger.info("Exporting %s and Anomaly transparent maps...", var_spec.display_name)
    periods = ["am", "af", "pm"]
    files = resolve_clipped_rasters(var_spec, maps_dir=INPUT_DIR, boundary_path=BOUNDARY_PATH)
    rasters = {p: load_uhi_raster(files[p]) for p in periods}
    raster_list = [rasters[p] for p in periods]
    shared_anom_lim = compute_shared_anomaly_limit(raster_list)

    # 1. Individual Value Maps
    temp_cmap = plt.get_cmap(TEMP_CMAP).copy()
    temp_cmap.set_bad(color="none", alpha=0.0)

    for p in periods:
        r = rasters[p]
        vmin, vmax = compute_temperature_limits(r)
        norm = Normalize(vmin=vmin, vmax=vmax)

        fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
        ax.set_facecolor("none")
        ax.imshow(r.data, extent=r.extent, cmap=temp_cmap, norm=norm, origin="upper", interpolation="bilinear")
        ax.set_xlim(r.extent[0], r.extent[1])
        ax.set_ylim(r.extent[2], r.extent[3])
        ax.set_aspect("equal")
        ax.axis("off")

        fname = f"{var_spec.value_file_prefix}_{p}_transparent.png"
        out_path = output_base / var_spec.value_subdir / fname
        save_transparent(fig, out_path, central_dir, fname)

    # 2. Individual Anomaly Maps
    anom_cmap = plt.get_cmap(ANOM_CMAP).copy()
    anom_cmap.set_bad(color="none", alpha=0.0)
    anom_norm = TwoSlopeNorm(vmin=-shared_anom_lim, vcenter=0.0, vmax=shared_anom_lim)

    for p in periods:
        r = rasters[p]
        fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
        ax.set_facecolor("none")
        ax.imshow(r.anomaly, extent=r.extent, cmap=anom_cmap, norm=anom_norm, origin="upper", interpolation="bilinear")
        ax.set_xlim(r.extent[0], r.extent[1])
        ax.set_ylim(r.extent[2], r.extent[3])
        ax.set_aspect("equal")
        ax.axis("off")

        fname = f"{var_spec.anomaly_file_prefix}_{p}_transparent.png"
        out_path = output_base / "anomaly" / fname
        save_transparent(fig, out_path, central_dir, fname)

    # 3. 3-Panel Value Map
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), facecolor="none", gridspec_kw={"wspace": 0.05})
    for ax, p in zip(axes, periods):
        r = rasters[p]
        vmin, vmax = compute_temperature_limits(r)
        norm = Normalize(vmin=vmin, vmax=vmax)
        ax.set_facecolor("none")
        ax.imshow(r.data, extent=r.extent, cmap=temp_cmap, norm=norm, origin="upper", interpolation="bilinear")
        ax.set_xlim(r.extent[0], r.extent[1])
        ax.set_ylim(r.extent[2], r.extent[3])
        ax.set_aspect("equal")
        ax.axis("off")

    panel_fname = f"{var_spec.value_file_prefix}_panel_transparent.png"
    out_panel_temp = output_base / "panels" / panel_fname
    save_transparent(fig, out_panel_temp, central_dir, panel_fname)

    # 4. 3-Panel Anomaly Map
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), facecolor="none", gridspec_kw={"wspace": 0.05})
    for ax, p in zip(axes, periods):
        r = rasters[p]
        ax.set_facecolor("none")
        ax.imshow(r.anomaly, extent=r.extent, cmap=anom_cmap, norm=anom_norm, origin="upper", interpolation="bilinear")
        ax.set_xlim(r.extent[0], r.extent[1])
        ax.set_ylim(r.extent[2], r.extent[3])
        ax.set_aspect("equal")
        ax.axis("off")

    anom_panel_fname = f"{var_spec.anomaly_file_prefix}_panel_transparent.png"
    out_panel_anom = output_base / "panels" / anom_panel_fname
    save_transparent(fig, out_panel_anom, central_dir, anom_panel_fname)


def export_canopy_maps(output_base: Path, central_dir: Path) -> None:
    """Export continuous, discrete quintile, and overview canopy transparent maps."""
    logger.info("Exporting Tree Canopy transparent maps...")
    if not CANOPY_GRID_PATH.is_file():
        logger.warning("Canopy grid not found: %s", CANOPY_GRID_PATH)
        return

    df = pyogrio.read_dataframe(CANOPY_GRID_PATH, read_geometry=False)
    b_gdf = gpd.read_file(BOUNDARY_PATH) if BOUNDARY_PATH.is_file() else None

    ncols = int(df["col_index"].max() - df["col_index"].min() + 1)
    nrows = int(df["row_index"].max() - df["row_index"].min() + 1)
    xmin = float(df["left"].min())
    xmax = float(df["right"].max())
    ymin = float(df["bottom"].min())
    ymax = float(df["top"].max())
    extent = [xmin, xmax, ymin, ymax]

    inside = df["coverage_frac"] > 0
    canopy_raw = df["canopy_pct"].values

    base_cmap = plt.get_cmap("YlGn").copy()
    base_cmap.set_bad(color="none", alpha=0.0)

    # 1. Continuous Canopy Map
    arr = np.full((nrows, ncols), np.nan, dtype=np.float32)
    arr[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = canopy_raw[inside]

    fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
    ax.set_facecolor("none")
    ax.imshow(arr, extent=extent, cmap=base_cmap, vmin=0.0, vmax=100.0, origin="upper", interpolation="nearest", zorder=2)
    if b_gdf is not None:
        b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    out_cont = output_base / "canopy" / "map_tree_canopy_transparent.png"
    save_transparent(fig, out_cont, central_dir, "map_tree_canopy_transparent.png")

    # Also save canopy_overview_transparent.png in output/canopy/
    fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
    ax.set_facecolor("none")
    ax.imshow(arr, extent=extent, cmap=base_cmap, vmin=0.0, vmax=100.0, origin="upper", interpolation="nearest", zorder=2)
    if b_gdf is not None:
        b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    out_over = output_base / "canopy" / "canopy_overview_transparent.png"
    save_transparent(fig, out_over, central_dir, "canopy_overview_transparent.png")

    # 2. Discrete 5-tier Quintile Canopy Map
    tier_colors = [base_cmap(0.12), base_cmap(0.32), base_cmap(0.52), base_cmap(0.72), base_cmap(0.92)]
    disc_cmap = ListedColormap(["none"] + tier_colors)

    disc_arr = np.zeros((nrows, ncols), dtype=int)
    binned = np.digitize(canopy_raw[inside], [0.0, 20.0, 40.0, 60.0, 80.0, 100.01])
    disc_arr[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = binned

    fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
    ax.set_facecolor("none")
    ax.imshow(disc_arr, extent=extent, cmap=disc_cmap, vmin=0, vmax=5, origin="upper", interpolation="nearest", zorder=2)
    if b_gdf is not None:
        b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    out_disc = output_base / "canopy" / "map_tree_canopy_discrete_transparent.png"
    save_transparent(fig, out_disc, central_dir, "map_tree_canopy_discrete_transparent.png")


def export_hotspot_and_significance_maps(var_spec: VariableSpec, output_base: Path, central_dir: Path) -> None:
    """Export hotspot persistence, spots by period, confidence tiers, and continuous z-score maps."""
    hotspots_gpkg = var_spec.hotspots_dir / "hotspots.gpkg"
    logger.info("Exporting Hotspot & Statistical Significance transparent maps (%s)...", var_spec.display_name)
    if not hotspots_gpkg.is_file():
        logger.warning("Hotspots GeoPackage not found: %s", hotspots_gpkg)
        return

    df = pyogrio.read_dataframe(hotspots_gpkg, read_geometry=False)
    b_gdf = gpd.read_file(BOUNDARY_PATH) if BOUNDARY_PATH.is_file() else None

    ncols = int(df["col_index"].max() - df["col_index"].min() + 1)
    nrows = int(df["row_index"].max() - df["row_index"].min() + 1)
    xmin = float(df["left"].min())
    xmax = float(df["right"].max())
    ymin = float(df["bottom"].min())
    ymax = float(df["top"].max())
    extent = [xmin, xmax, ymin, ymax]
    inside = df["coverage_frac"] > 0

    # 1. Hot & Cold Spots by Period (3-panel + individual)
    spot_cmap = ListedColormap(["none", COLOR_NS, COLOR_COLD, COLOR_HOT])
    periods = ["am", "af", "pm"]

    # 3-Panel spots by period
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), facecolor="none", gridspec_kw={"wspace": 0.05})
    for ax, p in zip(axes, periods):
        is_hot = df[f"is_hot_{p}"].values == 1
        is_cold = df[f"is_cold_{p}"].values == 1

        arr = np.zeros((nrows, ncols), dtype=int)
        arr[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = 1
        arr[df.loc[inside & is_cold, "row_index"].values, df.loc[inside & is_cold, "col_index"].values] = 2
        arr[df.loc[inside & is_hot, "row_index"].values, df.loc[inside & is_hot, "col_index"].values] = 3

        ax.set_facecolor("none")
        ax.imshow(arr, extent=extent, cmap=spot_cmap, vmin=0, vmax=3, origin="upper", interpolation="nearest", zorder=2)
        if b_gdf is not None:
            b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_HOTSPOTS, linewidth=0.85, zorder=3)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")

    out_spots_panel = output_base / "hotspots" / "map_spots_by_period_transparent.png"
    save_transparent(fig, out_spots_panel, central_dir, "map_spots_by_period_transparent.png")

    # Individual period spots
    for p in periods:
        is_hot = df[f"is_hot_{p}"].values == 1
        is_cold = df[f"is_cold_{p}"].values == 1

        arr = np.zeros((nrows, ncols), dtype=int)
        arr[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = 1
        arr[df.loc[inside & is_cold, "row_index"].values, df.loc[inside & is_cold, "col_index"].values] = 2
        arr[df.loc[inside & is_hot, "row_index"].values, df.loc[inside & is_hot, "col_index"].values] = 3

        fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
        ax.set_facecolor("none")
        ax.imshow(arr, extent=extent, cmap=spot_cmap, vmin=0, vmax=3, origin="upper", interpolation="nearest", zorder=2)
        if b_gdf is not None:
            b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_HOTSPOTS, linewidth=0.85, zorder=3)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")

        save_transparent(fig, output_base / "hotspots" / f"map_spots_{p}_transparent.png", central_dir, f"map_spots_{p}_transparent.png")

    # 2. Diurnal Persistence Map
    pers_palette = [
        "none",             # 0
        COLOR_NS,           # 1
        "#CBD5E1",          # 2
        COLOR_COLD_LIGHT,   # 3
        COLOR_COLD_MID,     # 4
        COLOR_COLD,         # 5
        COLOR_HOT_LIGHT,    # 6
        COLOR_HOT_MID,      # 7
        COLOR_HOT,          # 8
    ]
    pers_cmap = ListedColormap(pers_palette)

    n_hot = df["n_hot_periods"].values
    n_cold = df["n_cold_periods"].values

    arr_pers = np.zeros((nrows, ncols), dtype=int)
    # 1: NS
    arr_pers[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = 1
    # 2: Mixed
    mixed = inside & (n_hot > 0) & (n_cold > 0)
    arr_pers[df.loc[mixed, "row_index"].values, df.loc[mixed, "col_index"].values] = 2
    # Cold: 3, 4, 5
    for k in (1, 2, 3):
        m = inside & (n_cold == k) & (n_hot == 0)
        arr_pers[df.loc[m, "row_index"].values, df.loc[m, "col_index"].values] = 2 + k
    # Hot: 6, 7, 8
    for k in (1, 2, 3):
        m = inside & (n_hot == k) & (n_cold == 0)
        arr_pers[df.loc[m, "row_index"].values, df.loc[m, "col_index"].values] = 5 + k

    fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
    ax.set_facecolor("none")
    ax.imshow(arr_pers, extent=extent, cmap=pers_cmap, vmin=0, vmax=8, origin="upper", interpolation="nearest", zorder=2)
    if b_gdf is not None:
        b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_HOTSPOTS, linewidth=0.85, zorder=3)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    out_pers = output_base / "hotspots" / "map_persistence_transparent.png"
    save_transparent(fig, out_pers, central_dir, "map_persistence_transparent.png")

    # 3. Statistical Significance Confidence Tiers (7-tier: 3-panel + individual)
    conf_cmap = ListedColormap(["none"] + CONF_COLORS)

    def compute_conf_array(period_code: str) -> np.ndarray:
        z = df[f"gi_z_{period_code}"].values
        q = df[f"fdr_q_{period_code}"].values

        tier_code = np.zeros(len(df), dtype=int)
        c_ins = inside.values

        # Default inside -> 4 (Not Significant)
        tier_code[c_ins] = 4

        # Cold spots
        c90 = c_ins & (z <= -1.65) & (q <= 0.10)
        c95 = c_ins & (z <= -1.96) & (q <= 0.05)
        c99 = c_ins & (z <= -2.58) & (q <= 0.01)

        tier_code[c90] = 3
        tier_code[c95] = 2
        tier_code[c99] = 1

        # Hot spots
        h90 = c_ins & (z >= 1.65) & (q <= 0.10)
        h95 = c_ins & (z >= 1.96) & (q <= 0.05)
        h99 = c_ins & (z >= 2.58) & (q <= 0.01)

        tier_code[h90] = 5
        tier_code[h95] = 6
        tier_code[h99] = 7

        grid = np.zeros((nrows, ncols), dtype=int)
        grid[df.loc[c_ins, "row_index"].values, df.loc[c_ins, "col_index"].values] = tier_code[c_ins]
        return grid

    # Flagship Afternoon statistical significance map
    grid_af = compute_conf_array("af")
    fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
    ax.set_facecolor("none")
    ax.imshow(grid_af, extent=extent, cmap=conf_cmap, vmin=0, vmax=7, origin="upper", interpolation="nearest", zorder=2)
    if b_gdf is not None:
        b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    out_sig_af = output_base / "hotspots" / "map_statistical_significance_af_transparent.png"
    save_transparent(fig, out_sig_af, central_dir, "map_statistical_significance_af_transparent.png")

    # 3-Panel diurnal statistical significance map
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), facecolor="none", gridspec_kw={"wspace": 0.05})
    for ax, p in zip(axes, periods):
        grid_p = compute_conf_array(p)
        ax.set_facecolor("none")
        ax.imshow(grid_p, extent=extent, cmap=conf_cmap, vmin=0, vmax=7, origin="upper", interpolation="nearest", zorder=2)
        if b_gdf is not None:
            b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")

    out_sig_diurnal = output_base / "hotspots" / "map_statistical_significance_diurnal_transparent.png"
    save_transparent(fig, out_sig_diurnal, central_dir, "map_statistical_significance_diurnal_transparent.png")

    # Also individual AM and PM statistical significance
    for p in ["am", "pm"]:
        grid_p = compute_conf_array(p)
        fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
        ax.set_facecolor("none")
        ax.imshow(grid_p, extent=extent, cmap=conf_cmap, vmin=0, vmax=7, origin="upper", interpolation="nearest", zorder=2)
        if b_gdf is not None:
            b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")

        save_transparent(fig, output_base / "hotspots" / f"map_statistical_significance_{p}_transparent.png", central_dir, f"map_statistical_significance_{p}_transparent.png")

    # 4. Continuous Getis-Ord Gi* z-score Intensity Map (RdBu_r, adaptive limits >= +/- 8.0)
    z_cmap = plt.get_cmap("RdBu_r").copy()
    z_cmap.set_bad(color="none", alpha=0.0)
    z_all = np.concatenate([df.loc[inside, f"gi_z_{p}"].dropna().values for p in periods])
    z_p_ext = max(abs(float(np.percentile(z_all, 0.5))), abs(float(np.percentile(z_all, 99.5)))) if len(z_all) > 0 else 8.0
    z_lim = 8.0 if z_p_ext <= 8.5 else float(np.ceil(z_p_ext / 2.0) * 2.0)
    z_norm = TwoSlopeNorm(vmin=-z_lim, vcenter=0.0, vmax=z_lim)

    for p in periods:
        z_raw = df[f"gi_z_{p}"].values
        z_grid = np.full((nrows, ncols), np.nan, dtype=np.float32)
        z_grid[df.loc[inside, "row_index"].values, df.loc[inside, "col_index"].values] = z_raw[inside]

        fig, ax = plt.subplots(figsize=(8, 8), facecolor="none")
        ax.set_facecolor("none")
        ax.imshow(z_grid, extent=extent, cmap=z_cmap, norm=z_norm, origin="upper", interpolation="bilinear", zorder=2)
        if b_gdf is not None:
            b_gdf.boundary.plot(ax=ax, color=COLOR_BORDER_CANOPY, linewidth=0.85, zorder=3)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("equal")
        ax.axis("off")

        save_transparent(fig, output_base / "hotspots" / f"map_zscore_intensity_{p}_transparent.png", central_dir, f"map_zscore_intensity_{p}_transparent.png")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch generate map-only transparent PNGs at 300 DPI."
    )
    parser.add_argument(
        "--variable",
        choices=["temperature", "heat_index"],
        default="temperature",
        help="Target climatic variable (default: temperature)",
    )
    args = parser.parse_args()
    var_spec = get_variable_spec(args.variable)
    output_base = var_spec.figures_dir
    central_dir = output_base / "maps_transparent"

    logger.info("Starting batch generation of map-only transparent PNGs (%s)...", var_spec.display_name)
    export_temperature_and_anomaly_maps(var_spec, output_base, central_dir)
    if var_spec.key == "temperature":
        export_canopy_maps(output_base, central_dir)
    export_hotspot_and_significance_maps(var_spec, output_base, central_dir)

    # Summary
    central_files = list(central_dir.glob("*.png"))
    print("\n" + "=" * 70)
    print(f"SUCCESS: Generated {len(central_files)} transparent map-only figures at 300 DPI:")
    print("=" * 70)
    for f in sorted(central_files):
        size_kb = f.stat().st_size / 1024
        print(f"  • {f.name:<54} ({size_kb:.1f} KB)")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

