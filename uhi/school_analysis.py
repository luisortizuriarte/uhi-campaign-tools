"""
School Microclimate & Canopy Analysis Module
============================================
Performs 500-meter buffer zonal extractions for school locations across
Northern Virginia (Alexandria, Arlington, and Fairfax):
- Computes zonal median air temperatures for Morning (AM), Afternoon (AF), and Evening (PM).
- Computes spatial temperature anomalies relative to domain baseline means.
- Computes zonal tree canopy cover percentages from high-resolution canopy masks.
- Generates publication-grade, slide-ready figures (16:9 widescreen) adhering
  to the project's visual design standards.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import rasterio.mask

logger = logging.getLogger(__name__)

# Default file paths
DEFAULT_SCHOOL_LOCS = Path("output/locations/school_locs.gpkg")
DEFAULT_BUFFERS_GPKG = Path("output/locations/school_buffers_500m.gpkg")
DEFAULT_CANOPY_MASK = Path("output/canopy/canopy_mask_1m.tif")
DEFAULT_FIGURES_DIR = Path("output/figures/schools")

DEFAULT_RASTERS = {
    "am": Path("morning_clipped.tif"),
    "af": Path("afternoon_clipped.tif"),
    "pm": Path("evening_clipped.tif"),
}

# Regional domain means (°F) from NOVA campaign
DOMAIN_MEANS = {
    "am": 80.66463,
    "af": 95.39925,
    "pm": 93.06975,
}

# Visual design constants
SLIDE_FIGSIZE: Tuple[float, float] = (13.333, 7.5)
SLIDE_DPI: int = 300
FONT_FAMILY = "Figtree"
FALLBACK_FONTS = ["Figtree", "DejaVu Sans", "Arial", "sans-serif"]

PERIOD_CONFIG = {
    "am": {
        "title": "Morning School Microclimates: Hottest vs. Coolest 500m Buffers",
        "temp_col": "temp_med_am",
        "anom_col": "anom_med_am",
        "color": "#2980B9",
        "theme_color": "#2980B9",
        "edge_color": "#1A5276",
        "hot_color": "#D35400",
        "cool_color": "#2980B9",
        "label": "Morning (AM)",
    },
    "af": {
        "title": "Afternoon School Microclimates: Hottest vs. Coolest 500m Buffers",
        "temp_col": "temp_med_af",
        "anom_col": "anom_med_af",
        "color": "#F39C12",
        "theme_color": "#F39C12",
        "edge_color": "#B9770E",
        "hot_color": "#E67E22",
        "cool_color": "#2980B9",
        "label": "Afternoon (AF)",
    },
    "pm": {
        "title": "Evening School Microclimates: Hottest vs. Coolest 500m Buffers",
        "temp_col": "temp_med_pm",
        "anom_col": "anom_med_pm",
        "color": "#E74C3C",
        "theme_color": "#E74C3C",
        "edge_color": "#922B21",
        "hot_color": "#C0392B",
        "cool_color": "#2980B9",
        "label": "Evening (PM)",
    },
}


def _configure_figtree():
    """Ensure font family is configured for Matplotlib."""
    plt.rcParams["font.family"] = FALLBACK_FONTS


def compute_school_buffer_metrics(
    schools_path: Union[str, Path] = DEFAULT_SCHOOL_LOCS,
    buffer_distance: float = 500.0,
    rasters: Optional[Dict[str, Union[str, Path]]] = None,
    canopy_raster: Union[str, Path] = DEFAULT_CANOPY_MASK,
    output_gpkg: Optional[Union[str, Path]] = DEFAULT_BUFFERS_GPKG,
    layer_name: str = "school_buffers",
    update_points_gpkg: Optional[Union[str, Path]] = DEFAULT_SCHOOL_LOCS,
) -> gpd.GeoDataFrame:
    """
    Generate 500-meter circular buffers around school locations and extract zonal
    median air temperatures and tree canopy coverage.

    Parameters
    ----------
    schools_path : Union[str, Path]
        Path to school points GeoPackage.
    buffer_distance : float
        Radius in meters for the circular buffer (default: 500.0 m).
    rasters : Optional[Dict[str, Union[str, Path]]]
        Dictionary mapping period keys ('am', 'af', 'pm') to GeoTIFF paths.
    canopy_raster : Union[str, Path]
        Path to 1-meter high-resolution tree canopy mask GeoTIFF.
    output_gpkg : Optional[Union[str, Path]]
        Destination path to save the buffered polygons GeoPackage.
    layer_name : str
        Layer name inside destination GeoPackage.
    update_points_gpkg : Optional[Union[str, Path]]
        If provided, updates the point GeoPackage with the newly calculated metrics.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame of buffered polygons with temperature and canopy metrics.
    """
    if rasters is None:
        rasters = DEFAULT_RASTERS

    schools_p = Path(schools_path)
    if not schools_p.is_file():
        raise FileNotFoundError(f"Schools GeoPackage not found at: {schools_p}")

    logger.info("Loading school points from %s ...", schools_p)
    schools_pts = gpd.read_file(schools_p, layer="school_locs" if "school_locs" in schools_p.name else None)
    logger.info("Loaded %d school locations.", len(schools_pts))

    # Create 500-meter buffer
    logger.info("Creating %.1f-meter circular buffers...", buffer_distance)
    buffers_gdf = schools_pts.copy()
    buffers_gdf["geometry"] = schools_pts.geometry.buffer(buffer_distance)

    # 1. Extract zonal median temperatures for each period
    for period in ["am", "af", "pm"]:
        r_path = Path(rasters.get(period, DEFAULT_RASTERS[period]))
        if not r_path.is_file():
            logger.warning("Raster for %s not found at %s. Skipping.", period, r_path)
            buffers_gdf[f"temp_med_{period}"] = np.nan
            buffers_gdf[f"anom_med_{period}"] = np.nan
            continue

        logger.info("Extracting %s zonal median temperatures from %s ...", period.upper(), r_path.name)
        meds = []
        with rasterio.open(r_path) as src:
            for geom in buffers_gdf.geometry:
                try:
                    out_img, _ = rasterio.mask.mask(src, [geom], crop=True)
                    vals = out_img[0][~np.isnan(out_img[0])]
                    med = float(np.median(vals)) if len(vals) > 0 else np.nan
                except Exception:
                    med = np.nan
                meds.append(med)

        buffers_gdf[f"temp_med_{period}"] = meds
        domain_mean = DOMAIN_MEANS.get(period, np.nanmean(meds))
        buffers_gdf[f"anom_med_{period}"] = np.where(
            np.isfinite(meds),
            np.round(np.array(meds) - domain_mean, 2),
            np.nan,
        )
        logger.info(
            "Extracted %s: %d / %d valid (Median: %.2f °F, Anomaly: %+.2f °F)",
            period.upper(),
            np.isfinite(meds).sum(),
            len(buffers_gdf),
            np.nanmedian(meds),
            np.nanmedian(buffers_gdf[f"anom_med_{period}"]),
        )

    # 2. Extract zonal tree canopy coverage (%)
    c_path = Path(canopy_raster)
    if c_path.is_file():
        logger.info("Extracting zonal tree canopy cover (%%) from %s ...", c_path.name)
        canopy_pcts = []
        with rasterio.open(c_path) as src:
            for geom in buffers_gdf.geometry:
                try:
                    out_img, _ = rasterio.mask.mask(src, [geom], crop=True)
                    canopy_band = out_img[0]
                    study_band = out_img[1]
                    valid_study_pixels = (study_band == 1).sum()
                    if valid_study_pixels > 0:
                        pct = float((canopy_band[study_band == 1] == 1).sum() / valid_study_pixels * 100.0)
                    else:
                        pct = np.nan
                except Exception:
                    pct = np.nan
                canopy_pcts.append(pct)
        buffers_gdf["canopy_pct"] = np.round(canopy_pcts, 2)
        logger.info(
            "Extracted Canopy %%: %d / %d valid (Mean: %.1f%%, Min: %.1f%%, Max: %.1f%%)",
            np.isfinite(canopy_pcts).sum(),
            len(buffers_gdf),
            np.nanmean(canopy_pcts),
            np.nanmin(canopy_pcts),
            np.nanmax(canopy_pcts),
        )
    else:
        logger.warning("Canopy mask not found at %s. Setting canopy_pct to NaN.", c_path)
        buffers_gdf["canopy_pct"] = np.nan

    # Save buffers GeoPackage
    if output_gpkg:
        out_p = Path(output_gpkg)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Saving school buffers to %s (layer='%s') ...", out_p, layer_name)
        buffers_gdf.to_file(out_p, layer=layer_name, driver="GPKG")
        logger.info("Saved %d buffer polygons.", len(buffers_gdf))

    # Update point features GeoPackage with the same metrics
    if update_points_gpkg:
        pts_p = Path(update_points_gpkg)
        if pts_p.is_file():
            logger.info("Updating points layer in %s with extracted metrics ...", pts_p)
            updated_pts = schools_pts.copy()
            for col in [
                "temp_med_am",
                "temp_med_af",
                "temp_med_pm",
                "anom_med_am",
                "anom_med_af",
                "anom_med_pm",
                "canopy_pct",
            ]:
                if col in buffers_gdf.columns:
                    updated_pts[col] = buffers_gdf[col].values
            updated_pts.to_file(pts_p, layer="school_locs", driver="GPKG")
            logger.info("Successfully updated points layer in %s.", pts_p)

    return buffers_gdf


def plot_hottest_to_coldest_schools(
    df: gpd.GeoDataFrame,
    period: str = "af",
    output_path: Optional[Union[str, Path]] = None,
    n_top: int = 10,
    dpi: int = SLIDE_DPI,
) -> plt.Figure:
    """
    Generate a 16:9 presentation chart ranking school buffers from hottest to coolest
    and comparing the extremes for a given collection time.

    Parameters
    ----------
    df : gpd.GeoDataFrame
        DataFrame with school attributes and temperature metrics.
    period : str
        Collection period: 'am', 'af', or 'pm'.
    output_path : Optional[Union[str, Path]]
        File path to save the generated figure.
    n_top : int
        Number of schools to display in the hottest and coolest ranking groups (default: 10).
    dpi : int
        Resolution in DPI (default: 300).

    Returns
    -------
    matplotlib.figure.Figure
    """
    _configure_figtree()
    period = period.lower()
    if period not in PERIOD_CONFIG:
        raise ValueError(f"Unknown period '{period}'. Expected 'am', 'af', or 'pm'.")

    cfg = PERIOD_CONFIG[period]
    col = cfg["temp_col"]

    valid = df.dropna(subset=[col]).sort_values(col, ascending=True).copy()
    n_total = len(valid)
    if n_total == 0:
        raise ValueError(f"No valid records for column '{col}'.")

    coolest = valid.head(n_top).copy()
    hottest = valid.tail(n_top).copy()

    hot_school = valid.iloc[-1]
    cool_school = valid.iloc[0]
    delta_t = hot_school[col] - cool_school[col]
    median_val = valid[col].median()

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")

    # Left: Ranked Horizontal Bar Chart
    ax_bars = fig.add_axes([0.28, 0.12, 0.38, 0.74])

    for s in ax_bars.spines.values():
        s.set_visible(False)
    ax_bars.tick_params(left=False, bottom=False, labelbottom=False)

    y_cool = np.arange(n_top)
    gap = 2.0
    y_hot = np.arange(n_top + gap, 2 * n_top + gap)

    bar_h = 0.65
    x_min_baseline = cool_school[col] - 1.2

    # Coolest bars
    bars_cool = ax_bars.barh(
        y_cool,
        coolest[col] - x_min_baseline,
        height=bar_h,
        left=x_min_baseline,
        color=cfg["cool_color"],
        edgecolor="none",
    )

    # Hottest bars
    bars_hot = ax_bars.barh(
        y_hot,
        hottest[col] - x_min_baseline,
        height=bar_h,
        left=x_min_baseline,
        color=cfg["hot_color"],
        edgecolor="none",
    )

    # Y tick labels (School Name + Jurisdiction)
    y_ticks = list(y_cool) + list(y_hot)
    y_labels = (
        [f"{r['school_name']} ({r.get('county_code', r['jurisdiction'])})" for _, r in coolest.iterrows()]
        + [f"{r['school_name']} ({r.get('county_code', r['jurisdiction'])})" for _, r in hottest.iterrows()]
    )

    ax_bars.set_yticks(y_ticks)
    ax_bars.set_yticklabels(y_labels, fontsize=10.5, fontweight="medium", color="#1F2937", fontfamily=FONT_FAMILY)

    # Direct value annotations
    for bar, val in zip(bars_cool, coolest[col]):
        ax_bars.text(
            val + 0.12,
            bar.get_y() + bar.get_height() / 2.0,
            f"{val:.2f}°F",
            ha="left",
            va="center",
            fontsize=10,
            weight="bold",
            color=cfg["cool_color"],
            fontfamily=FONT_FAMILY,
        )

    for bar, val in zip(bars_hot, hottest[col]):
        ax_bars.text(
            val + 0.12,
            bar.get_y() + bar.get_height() / 2.0,
            f"{val:.2f}°F",
            ha="left",
            va="center",
            fontsize=10,
            weight="bold",
            color=cfg["hot_color"],
            fontfamily=FONT_FAMILY,
        )

    # Section Headers
    ax_bars.text(
        x_min_baseline,
        2 * n_top + gap - 0.2,
        f"TOP {n_top} HOTTEST SCHOOLS",
        fontsize=11,
        weight="bold",
        color=cfg["hot_color"],
        fontfamily=FONT_FAMILY,
        va="bottom",
    )
    ax_bars.text(
        x_min_baseline,
        n_top - 0.2,
        f"TOP {n_top} COOLEST SCHOOLS",
        fontsize=11,
        weight="bold",
        color=cfg["cool_color"],
        fontfamily=FONT_FAMILY,
        va="bottom",
    )

    ax_bars.set_xlim(x_min_baseline, hot_school[col] + 1.8)
    ax_bars.set_ylim(-1.0, 2 * n_top + gap + 1.2)

    # Reference median line on bars
    ax_bars.axvline(median_val, color="#BDC3C7", linestyle="--", linewidth=1.2, zorder=0)
    ax_bars.text(
        median_val,
        2 * n_top + gap + 0.8,
        f"Median: {median_val:.2f}°F",
        ha="center",
        va="bottom",
        fontsize=10,
        color="#7F8C8D",
        fontfamily=FONT_FAMILY,
    )

    # Right Top: Summary Card
    ax_card = fig.add_axes([0.71, 0.52, 0.24, 0.34])
    ax_card.axis("off")

    card_rect = mpatches.FancyBboxPatch(
        (0, 0),
        1,
        1,
        boxstyle="round,pad=0.08,rounding_size=0.06",
        facecolor="#ECF0F1",
        edgecolor="none",
        transform=ax_card.transAxes,
        clip_on=False,
    )
    ax_card.add_patch(card_rect)

    ax_card.text(
        0.5,
        0.92,
        "MICROCLIMATE CONTRAST",
        ha="center",
        va="top",
        fontsize=11,
        weight="bold",
        color="#7F8C8D",
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )
    ax_card.text(
        0.5,
        0.74,
        f"Range: {delta_t:.2f} °F",
        ha="center",
        va="top",
        fontsize=20,
        weight="bold",
        color=cfg["hot_color"],
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )
    ax_card.text(
        0.5,
        0.58,
        f"Max Spread across {n_total} Schools",
        ha="center",
        va="top",
        fontsize=10,
        color="#1F2937",
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )

    div_line = plt.Line2D([0.08, 0.92], [0.50, 0.50], color="#BDC3C7", linewidth=1, transform=ax_card.transAxes)
    ax_card.add_line(div_line)

    ax_card.text(
        0.08,
        0.42,
        "HOTTEST SCHOOL BUFFER",
        ha="left",
        va="top",
        fontsize=9.5,
        weight="bold",
        color=cfg["hot_color"],
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )
    ax_card.text(
        0.08,
        0.32,
        f"{hot_school['school_name']}\n{hot_school[col]:.2f} °F ({hot_school['jurisdiction']})",
        ha="left",
        va="top",
        fontsize=10,
        color="#1F2937",
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )

    ax_card.text(
        0.08,
        0.16,
        "COOLEST SCHOOL BUFFER",
        ha="left",
        va="top",
        fontsize=9.5,
        weight="bold",
        color=cfg["cool_color"],
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )
    ax_card.text(
        0.08,
        0.06,
        f"{cool_school['school_name']}\n{cool_school[col]:.2f} °F ({cool_school['jurisdiction']})",
        ha="left",
        va="top",
        fontsize=10,
        color="#1F2937",
        fontfamily=FONT_FAMILY,
        transform=ax_card.transAxes,
    )

    # Right Bottom: Full Distribution Rank Curve
    ax_dist = fig.add_axes([0.71, 0.12, 0.24, 0.32])
    for s in ax_dist.spines.values():
        s.set_visible(False)
    ax_dist.spines["bottom"].set_visible(True)
    ax_dist.spines["bottom"].set_color("#BDC3C7")
    ax_dist.grid(axis="y", linestyle=":", alpha=0.6, color="#BDC3C7")

    ranks = np.arange(1, n_total + 1)
    sorted_temps = valid[col].values

    ax_dist.plot(ranks, sorted_temps, color=cfg["theme_color"], linewidth=2.5, zorder=3)
    ax_dist.fill_between(ranks, cool_school[col] - 0.5, sorted_temps, color=cfg["theme_color"], alpha=0.15, zorder=2)

    mid_idx = n_total // 2
    ax_dist.scatter([1], [cool_school[col]], color=cfg["cool_color"], s=45, zorder=5)
    ax_dist.scatter([mid_idx], [sorted_temps[mid_idx]], color="#7F8C8D", s=40, zorder=5)
    ax_dist.scatter([n_total], [hot_school[col]], color=cfg["hot_color"], s=45, zorder=5)

    ax_dist.set_title(
        f"Full Distribution of All Schools (N = {n_total})",
        fontsize=11,
        weight="bold",
        color="#1F2937",
        fontfamily=FONT_FAMILY,
        pad=8,
    )
    ax_dist.set_xlabel("Coolest → Hottest Rank (1 to 261)", fontsize=10, color="#1F2937", fontfamily=FONT_FAMILY)
    ax_dist.set_ylabel("Temp (°F)", fontsize=10, color="#1F2937", fontfamily=FONT_FAMILY)
    ax_dist.tick_params(colors="#1F2937", labelsize=9.5)
    ax_dist.set_ylim(cool_school[col] - 0.5, hot_school[col] + 0.5)

    # Overall Title
    fig.text(
        0.08,
        0.94,
        cfg["title"],
        ha="left",
        va="top",
        fontsize=16,
        weight="bold",
        fontfamily=FONT_FAMILY,
        color="#1F2937",
    )

    # Overall Caption
    fig.text(
        0.50,
        0.035,
        "Zonal median air temperatures (°F) within 500-meter circular buffers around school centroids • Northern Virginia Heat Watch Campaign",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#7F8C8D",
        fontfamily=FONT_FAMILY,
        style="italic",
    )

    if output_path:
        out_f = Path(output_path)
        out_f.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_f, dpi=dpi, facecolor="#FFFFFF")
        logger.info("Saved hottest to coldest school figure to %s", out_f)

    return fig


def plot_school_canopy_vs_anomaly(
    df: gpd.GeoDataFrame,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = SLIDE_DPI,
) -> plt.Figure:
    """
    Generate a 16:9 presentation multi-series scatter plot summarizing the relationship
    between school buffer temperature anomaly and tree canopy cover across Morning, Afternoon,
    and Evening.

    Parameters
    ----------
    df : gpd.GeoDataFrame
        DataFrame with canopy_pct and anom_med_am, anom_med_af, anom_med_pm columns.
    output_path : Optional[Union[str, Path]]
        File path to save the generated figure.
    dpi : int
        Resolution in DPI (default: 300).

    Returns
    -------
    matplotlib.figure.Figure
    """
    _configure_figtree()

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")

    # Layout geometry leaving margins for title/legend and bottom caption
    ax = fig.add_axes([0.08, 0.16, 0.88, 0.62])

    for s in ax.spines.values():
        s.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#BDC3C7")
    ax.spines["bottom"].set_linewidth(1.2)

    ax.grid(axis="y", linestyle=":", alpha=0.6, color="#BDC3C7")
    ax.set_axisbelow(True)

    # Reference zero line (spatial mean)
    ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2, zorder=1)

    legend_handles = []
    stats_lines = []

    for period in ["am", "af", "pm"]:
        cfg = PERIOD_CONFIG[period]
        col = cfg["anom_col"]
        color = cfg["color"]
        edge = cfg["edge_color"]
        lbl = cfg["label"]

        sub = df.dropna(subset=["canopy_pct", col]).copy()
        if len(sub) == 0:
            continue

        x = sub["canopy_pct"].values
        y = sub[col].values

        # Scatter points
        ax.scatter(
            x,
            y,
            s=48,
            color=color,
            edgecolor=edge,
            linewidth=0.7,
            alpha=0.65,
            zorder=3,
            label=lbl,
        )

        # OLS regression
        slope, intercept = np.polyfit(x, y, 1)
        corr = np.corrcoef(x, y)[0, 1]
        r2 = corr**2

        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, color=color, linewidth=2.4, zorder=4)

        # 95% Confidence Interval band
        n = len(x)
        dof = n - 2
        residuals = y - (slope * x + intercept)
        s_err = np.sqrt(np.sum(residuals**2) / dof)
        ci = 1.96 * s_err * np.sqrt(1 / n + (x_line - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2))
        ax.fill_between(x_line, y_line - ci, y_line + ci, color=color, alpha=0.15, zorder=2)

        delta_10 = slope * 10.0
        stats_lines.append(
            {
                "label": lbl,
                "color": color,
                "r": corr,
                "r2": r2,
                "slope_10": delta_10,
            }
        )

        legend_handles.append(mpatches.Patch(facecolor=color, edgecolor="none", label=lbl))

    # Lowered Horizontal Legend: Centered, 3 columns, square markers, rounded light gray container
    leg = ax.legend(
        handles=legend_handles,
        ncols=3,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.98),
        frameon=True,
        facecolor="#ECF0F1",
        edgecolor="none",
        handlelength=1.0,
        handleheight=1.0,
        borderpad=0.6,
        columnspacing=2.5,
        handletextpad=0.6,
        prop={"family": FONT_FAMILY, "weight": "bold", "size": 11.5},
    )
    if leg.get_frame():
        leg.get_frame().set_boxstyle("round,pad=0.5,rounding_size=0.3")

    ax.set_xlabel(
        "Tree Canopy Cover within 500m School Buffer (%)",
        fontsize=13,
        weight="bold",
        color="#1F2937",
        labelpad=12,
        fontfamily=FONT_FAMILY,
    )
    ax.set_ylabel(
        "Temperature Anomaly (°F)",
        fontsize=13,
        weight="bold",
        color="#1F2937",
        labelpad=10,
        fontfamily=FONT_FAMILY,
    )
    ax.tick_params(colors="#1F2937", labelsize=11)
    ax.set_xlim(10, 80)
    ax.set_ylim(-3.8, 3.8)

    # Statistics callout cards in lower right
    stats_box_y = 0.28
    for st in stats_lines:
        txt = f"{st['label']}:  r = {st['r']:+.2f}  •  R² = {st['r2']:.2f}  •  Cooling: {st['slope_10']:+.2f} °F / 10% canopy"
        ax.text(
            0.98,
            stats_box_y,
            txt,
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=10.5,
            weight="bold",
            color=st["color"],
            fontfamily=FONT_FAMILY,
            bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.2", facecolor="#ECF0F1", edgecolor="none", alpha=0.9),
        )
        stats_box_y -= 0.08

    # Title
    fig.text(
        0.08,
        0.94,
        "School Buffer Temperature Anomaly vs. Tree Canopy Cover",
        ha="left",
        va="top",
        fontsize=16,
        weight="bold",
        fontfamily=FONT_FAMILY,
        color="#1F2937",
    )

    # Caption
    fig.text(
        0.50,
        0.035,
        "Linear regression trendlines with 95% confidence intervals • Temperature anomaly relative to domain mean • Northern Virginia Heat Watch Campaign (N = 261 schools)",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#7F8C8D",
        fontfamily=FONT_FAMILY,
        style="italic",
    )

    if output_path:
        out_f = Path(output_path)
        out_f.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_f, dpi=dpi, facecolor="#FFFFFF")
        logger.info("Saved canopy vs anomaly figure to %s", out_f)

    return fig
