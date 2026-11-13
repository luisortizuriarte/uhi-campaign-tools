"""
uhi/analysis.py - Analysis and charting routines comparing tree canopy cover to temperature and anomaly.

Generates presentation-ready 16:9 figures:
1. Scatter plots with density hexbins and linear regression trendlines.
2. Grouped and individual bar charts of canopy quintiles with 95% confidence intervals.
3. Grouped and individual boxplots displaying full distribution, median, and IQR.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyogrio
from scipy import stats

from uhi.variables import get_variable_spec

# Configure global default font to Figtree
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Figtree", "DejaVu Sans"]

logger = logging.getLogger(__name__)

SLIDE_FIGSIZE: Tuple[float, float] = (13.333, 7.5)
DEFAULT_DPI: int = 300

VARIABLE_CONFIG: Dict[str, Dict[str, Union[str, bool]]] = {
    # Absolute Temperature
    "temp_am": {
        "period": "am",
        "label": "Morning (AM)",
        "full_title": "Morning (AM) Air Temperature",
        "ylabel": "Morning (AM) Air Temperature (°F)",
        "unit": "°F",
        "color": "#2563EB",  # Vibrant Blue
        "light_color": "#BFDBFE",
        "cmap": "Blues",
        "is_anomaly": False,
    },
    "temp_af": {
        "period": "af",
        "label": "Afternoon (AF)",
        "full_title": "Afternoon (AF) Air Temperature",
        "ylabel": "Afternoon (AF) Air Temperature (°F)",
        "unit": "°F",
        "color": "#DC2626",  # Vibrant Red
        "light_color": "#FECACA",
        "cmap": "YlOrRd",
        "is_anomaly": False,
    },
    "temp_pm": {
        "period": "pm",
        "label": "Evening (PM)",
        "full_title": "Evening (PM) Air Temperature",
        "ylabel": "Evening (PM) Air Temperature (°F)",
        "unit": "°F",
        "color": "#7C3AED",  # Deep Purple
        "light_color": "#DDD6FE",
        "cmap": "Purples",
        "is_anomaly": False,
    },
    # Temperature Spatial Anomaly (T - spatial_mean)
    # Requested palette: Morning: #2980B9, Afternoon: #F39C12, Evening: #E74C3C
    "anom_am": {
        "period": "am",
        "label": "Morning (AM)",
        "full_title": "Morning (AM) Temperature Anomaly",
        "ylabel": "Morning (AM) Temperature Anomaly (°F)",
        "unit": "°F",
        "color": "#2980B9",  # Darker Blue
        "light_color": "#EBF5FB",
        "cmap": "Blues",
        "is_anomaly": True,
    },
    "anom_af": {
        "period": "af",
        "label": "Afternoon (AF)",
        "full_title": "Afternoon (AF) Temperature Anomaly",
        "ylabel": "Afternoon (AF) Temperature Anomaly (°F)",
        "unit": "°F",
        "color": "#F39C12",  # Amber / Orange
        "light_color": "#FEF9E7",
        "cmap": "YlOrRd",
        "is_anomaly": True,
    },
    "anom_pm": {
        "period": "pm",
        "label": "Evening (PM)",
        "full_title": "Evening (PM) Temperature Anomaly",
        "ylabel": "Evening (PM) Temperature Anomaly (°F)",
        "unit": "°F",
        "color": "#E74C3C",  # Flat UI Red
        "light_color": "#FDEDEC",
        "cmap": "Purples",
        "is_anomaly": True,
    },
}

# Compatibility aliases
TIME_CONFIG = {k: v for k, v in VARIABLE_CONFIG.items() if not v["is_anomaly"]}
ANOM_CONFIG = {k: v for k, v in VARIABLE_CONFIG.items() if v["is_anomaly"]}

QUINTILE_BINS = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
QUINTILE_LABELS = ["0–20%\n(Q1)", "20–40%\n(Q2)", "40–60%\n(Q3)", "60–80%\n(Q4)", "80–100%\n(Q5)"]
QUINTILE_SHORT_LABELS = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]


def _get_col_meta(var_col: str, variable: str = "temperature") -> Dict[str, Union[str, bool]]:
    """Return display metadata for a column adapted to the chosen variable ('temperature' or 'heat_index')."""
    if var_col not in VARIABLE_CONFIG:
        raise KeyError(f"Unknown variable column '{var_col}'. Available: {list(VARIABLE_CONFIG.keys())}")
    cfg = dict(VARIABLE_CONFIG[var_col])
    spec = get_variable_spec(variable)
    if spec.key != "temperature":
        cfg["full_title"] = (
            str(cfg["full_title"])
            .replace("Air Temperature", spec.display_name)
            .replace("Temperature Anomaly", f"{spec.short_name} Anomaly")
        )
        cfg["ylabel"] = (
            str(cfg["ylabel"])
            .replace("Air Temperature", spec.display_name)
            .replace("Temperature Anomaly", f"{spec.short_name} Anomaly")
        )
    return cfg


def load_analysis_dataframe(gpkg_path: Union[str, Path]) -> pd.DataFrame:
    """Load grid data and prepare cleaned analysis dataframe with canopy quintiles and anomalies."""
    p = Path(gpkg_path)
    if not p.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {p}")

    df = pyogrio.read_dataframe(p, read_geometry=False)
    req_cols = ["canopy_pct", "temp_am", "temp_af", "temp_pm"]
    for c in req_cols:
        if c not in df.columns:
            raise KeyError(f"Missing required column '{c}' in {p}")

    # Keep records inside study area with valid temperature and canopy
    valid = df.dropna(subset=req_cols).copy()

    # Ensure anomaly columns exist
    for period in ["am", "af", "pm"]:
        t_col = f"temp_{period}"
        a_col = f"anom_{period}"
        if a_col not in valid.columns:
            valid[a_col] = np.round(valid[t_col] - valid[t_col].mean(), 2)

    valid["quintile"] = pd.cut(
        valid["canopy_pct"],
        bins=QUINTILE_BINS,
        include_lowest=True,
        labels=QUINTILE_SHORT_LABELS,
    )
    return valid


def plot_scatter_canopy_temp(
    df: pd.DataFrame,
    var_col: str,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = DEFAULT_DPI,
    variable: str = "temperature",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Generate a 16:9 scatter plot with hexbin density and linear regression trendline.
    Supports both absolute temperature/heat index and spatial anomaly.
    """
    cfg = _get_col_meta(var_col, variable)
    is_anomaly = bool(cfg["is_anomaly"])

    x = df["canopy_pct"].values
    y = df[var_col].values

    # Linear regression
    slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)
    r2 = r_val ** 2

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")
    ax = fig.add_axes([0.10, 0.14, 0.74, 0.72])

    # Hexbin 2D density to handle 100k+ points cleanly without overplotting
    hb = ax.hexbin(
        x,
        y,
        gridsize=85,
        cmap=cfg["cmap"],
        mincnt=1,
        bins="log",
        edgecolors="none",
        alpha=0.92,
    )

    # Reference zero line for anomaly
    if is_anomaly:
        ax.axhline(0, color="#6B7280", linestyle=":", linewidth=1.6, alpha=0.85, zorder=3)

    # Add regression trendline
    x_line = np.linspace(0, 100, 200)
    y_line = slope * x_line + intercept
    ax.plot(x_line, y_line, color="#111827", linewidth=2.8, linestyle="--", label="Linear Trend", zorder=5)

    # Colorbar for density
    cbar_ax = fig.add_axes([0.86, 0.18, 0.02, 0.64])
    cbar = fig.colorbar(hb, cax=cbar_ax, orientation="vertical")
    cbar.set_label("Cell Count (log₁₀ scale)", fontsize=11, weight="bold", color="#374151", fontfamily="Figtree")
    cbar.ax.tick_params(labelsize=10)

    # Axis formatting
    ax.set_xlabel("Tree Canopy Cover (%)", fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
    ax.set_ylabel(cfg["ylabel"], fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
    ax.set_xlim(-2, 102)

    if is_anomaly:
        y_abs_max = max(abs(np.percentile(y, 0.1)), abs(np.percentile(y, 99.9)))
        y_lim = max(np.ceil(y_abs_max) + 1.0, 7.5)
        ax.set_ylim(-y_lim, y_lim)
    else:
        y_min, y_max = np.floor(y.min()) - 0.5, np.ceil(y.max()) + 0.5
        ax.set_ylim(y_min, y_max)

    ax.grid(True, linestyle=":", alpha=0.6, color="#9CA3AF")
    ax.tick_params(labelsize=11, colors="#374151")

    # Annotation box with statistical parameters
    delta_100 = slope * 100.0  # Cooling across 0% to 100% canopy
    spec = get_variable_spec(variable)
    base_sym = "HI" if spec.key == "heat_index" else "T"
    fit_symbol = f"{base_sym}_anom" if is_anomaly else base_sym
    stats_text = (
        f"Linear Fit: {fit_symbol} = {slope:+.3f} × Canopy + {intercept:.2f}\n"
        f"Pearson r:  {r_val:+.3f}  (R² = {r2:.3f})\n"
        f"Cooling (0% → 100% canopy): {delta_100:+.2f} °F\n"
        f"Sample size: N = {len(df):,} grid cells"
    )
    ax.text(
        0.04,
        0.10,
        stats_text,
        transform=ax.transAxes,
        fontsize=11.5,
        fontfamily="Figtree",
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#FFFFFF", edgecolor="#D1D5DB", alpha=0.92),
        zorder=6,
    )

    # Titles
    fig.suptitle(
        f"Tree Canopy Cover vs. {cfg['full_title']}",
        fontsize=17,
        weight="bold",
        color="#111827",
        fontfamily="Figtree",
        y=0.95,
    )
    subtitle = (
        "100m grid cell analysis across Northern Virginia • Relative to spatial mean (0 °F baseline)"
        if is_anomaly
        else "100m grid cell analysis across Northern Virginia (NOVA Heat Watch Campaign)"
    )
    fig.text(
        0.47,
        0.89,
        subtitle,
        ha="center",
        fontsize=11.5,
        color="#4B5563",
        style="italic",
        fontfamily="Figtree",
    )

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
        logger.info("Saved scatter plot: %s", out)

    return fig, ax


def plot_grouped_barchart(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = DEFAULT_DPI,
    variable: str = "temperature",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Generate a 16:9 grouped bar chart of temperature, heat index, or anomaly across canopy quintiles
    with 95% confidence intervals for AM, AF, and PM.

    When plotting anomalies, applies clean presentation styling:
    - Removes bar edges.
    - Removes top, left, and right axes (spines).
    - Removes y label and y ticks.
    - Removes frame of legend.
    - Uses Figtree font.
    - Moves suptitle to a caption at the bottom, below all figure elements.
    - Matches bar label colors to their respective bar colors.
    """
    if cols is None:
        cols = ["temp_am", "temp_af", "temp_pm"]

    spec = get_variable_spec(variable)
    col_cfgs = [_get_col_meta(c, variable) for c in cols]
    is_anomaly = any(bool(cfg.get("is_anomaly", False)) for cfg in col_cfgs)

    agg_stats = []
    all_tops = []
    all_bots = []
    for c in cols:
        agg = df.groupby("quintile", observed=False)[c].agg(["mean", "sem"])
        means = agg["mean"].values
        ci95 = 1.96 * agg["sem"].values
        agg_stats.append((means, ci95))
        all_tops.extend((means + np.nan_to_num(ci95)).tolist())
        all_bots.extend((means - np.nan_to_num(ci95)).tolist())

    data_max = float(np.nanmax(all_tops))
    data_min = float(np.nanmin(all_bots))
    data_span = max(data_max - min(data_min, 0.0) if is_anomaly else data_max - data_min, 2.0)

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")

    n_groups = len(QUINTILE_SHORT_LABELS)
    indices = np.arange(n_groups)
    bar_width = 0.24

    if is_anomaly:
        # Leave room at top for title (y=0.94) and lowered centered legend, and bottom for spectrum guide and caption
        ax = fig.add_axes([0.08, 0.22, 0.88, 0.56])

        # Remove top, left, right, and bottom axes
        ax.spines["top"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)

        # Remove y label & ticks
        ax.tick_params(left=False, labelleft=False, bottom=False)

        # Frame categories cleanly
        ax.set_xlim(-0.55, n_groups - 0.45)

        # Zero reference line across category span
        ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2, zorder=1)
    else:
        ax = fig.add_axes([0.08, 0.14, 0.88, 0.72])
        ax.set_ylabel(f"Mean {spec.display_name} ({spec.unit})", fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
        y_floor = float(np.floor((data_min - max(4.0, data_span * 0.18)) / 2.0) * 2.0)
        y_ceil = float(np.ceil((data_max + max(5.5, data_span * 0.34)) / 2.0) * 2.0)
        ax.set_ylim(y_floor, y_ceil)
        ax.grid(axis="y", linestyle=":", alpha=0.7, color="#9CA3AF", zorder=0)

    anom_txt_gap = max(0.10, data_span * 0.025)
    abs_txt_gap = max(0.35, data_span * 0.015)

    for i, (col, cfg, (means, ci95)) in enumerate(zip(cols, col_cfgs, agg_stats)):
        offset = (i - 1) * bar_width
        pos = indices + offset

        if is_anomaly:
            bars = ax.bar(
                pos,
                means,
                bar_width,
                yerr=ci95,
                capsize=3.5,
                error_kw=dict(ecolor=cfg["color"], lw=1.3, capthick=1.3),
                color=cfg["color"],
                edgecolor="none",
                linewidth=0,
                label=cfg["label"],
                zorder=3,
            )

            # Bar text label: same color as the corresponding bar
            for bar, m, ci in zip(bars, means, ci95):
                if m >= 0:
                    y_txt = m + ci + anom_txt_gap
                    va = "bottom"
                else:
                    y_txt = m - ci - anom_txt_gap
                    va = "top"
                txt = f"{m:+.2f}°"
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    y_txt,
                    txt,
                    ha="center",
                    va=va,
                    fontsize=10.5,
                    weight="bold",
                    color=cfg["color"],
                    fontfamily="Figtree",
                    zorder=4,
                )
        else:
            bars = ax.bar(
                pos,
                means,
                bar_width,
                yerr=ci95,
                capsize=4.5,
                color=cfg["color"],
                edgecolor="#1E293B",
                linewidth=1.0,
                label=cfg["label"],
                zorder=3,
            )
            for bar, m, ci in zip(bars, means, ci95):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + np.nan_to_num(ci) + abs_txt_gap,
                    f"{m:.1f}°",
                    ha="center",
                    va="bottom",
                    fontsize=9.2,
                    weight="bold",
                    color="#1F2937",
                    fontfamily="Figtree",
                    zorder=4,
                )

    if is_anomaly:
        y_anom_min = min(-3.1, float(np.floor((min(data_min, 0.0) - max(0.65, data_span * 0.16)) * 10) / 10))
        y_anom_max = max(2.8, float(np.ceil((max(data_max, 0.0) + max(0.85, data_span * 0.25)) * 10) / 10))
        ax.set_ylim(y_anom_min, y_anom_max)

        # 1. Spectrum Directional Guide placed directly ABOVE the x labels in #16A085 without background box (narrowed span)
        dots = " · " * 18
        spectrum_str = f"←  LEAST TREE CANOPY  {dots}  MOST TREE CANOPY  →"
        fig.text(
            0.529,
            0.205,
            spectrum_str,
            ha="center",
            va="center",
            fontsize=14,
            weight="bold",
            color="#16A085",
            fontfamily="Figtree",
        )

        clean_labels = [
            "0–20%",
            "20–40%",
            "40–60%",
            "60–80%",
            "80–100%",
        ]
        ax.set_xticks(indices)
        ax.tick_params(axis="x", pad=26)
        ax.set_xticklabels(clean_labels, fontsize=12, color="#1F2937", fontfamily="Figtree")

        # X-axis Title
        fig.text(
            0.529,
            0.090,
            "Tree Canopy Cover Quintiles (Q1 to Q5)",
            ha="center",
            va="center",
            fontsize=12.5,
            weight="bold",
            color="#1F2937",
            fontfamily="Figtree",
        )

        # Large title at top and left aligned
        fig.text(
            0.08,
            0.94,
            f"Mean {spec.display_name} Anomaly by Tree Canopy Quintile & Collection Time",
            ha="left",
            va="top",
            fontsize=16,
            weight="bold",
            fontfamily="Figtree",
            color="#1F2937",
        )

        # Legend: 3 columns, square markers, centered at top, background #ECF0F1 (clean labels without AM/AF/PM)
        clean_legend_names = {"anom_am": "Morning", "anom_af": "Afternoon", "anom_pm": "Evening",
                              "temp_am": "Morning", "temp_af": "Afternoon", "temp_pm": "Evening"}
        legend_handles = [
            matplotlib.patches.Patch(facecolor=col_cfgs[idx]["color"], edgecolor="none", label=clean_legend_names.get(c, col_cfgs[idx]["label"]))
            for idx, c in enumerate(cols)
        ]
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
            prop={"family": "Figtree", "weight": "bold", "size": 11.5},
        )
        leg.get_frame().set_boxstyle("round,pad=0.5,rounding_size=0.3")

        # Bottom caption
        fig.text(
            0.50,
            0.030,
            "Quintiles divide Northern Virginia land into 5 equal 20% steps of tree cover • Error bars represent 95% confidence intervals • Baseline at 0 °F (Spatial Mean)",
            ha="center",
            va="center",
            fontsize=10.5,
            style="italic",
            fontfamily="Figtree",
            color="#7F8C8D",
        )
    else:
        ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=13, weight="bold", color="#1F2937", labelpad=12, fontfamily="Figtree")
        ax.set_xticks(indices)
        ax.set_xticklabels(QUINTILE_LABELS, fontsize=12, color="#1F2937", fontfamily="Figtree")
        ax.legend(fontsize=12, frameon=True, facecolor="#FFFFFF", edgecolor="#D1D5DB", loc="upper right")
        fig.suptitle(f"Mean {spec.display_name} by Tree Canopy Quintile & Collection Time", fontsize=17, weight="bold", color="#111827", fontfamily="Figtree", y=0.95)
        fig.text(0.52, 0.89, "Error bars represent 95% confidence intervals of the mean • Northern Virginia Heat Watch Campaign", ha="center", fontsize=11.5, color="#4B5563", style="italic", fontfamily="Figtree")

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
        logger.info("Saved grouped bar chart: %s", out)

    return fig, ax


def plot_single_barchart(
    df: pd.DataFrame,
    var_col: str,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = DEFAULT_DPI,
    variable: str = "temperature",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Generate an individual 16:9 bar chart for a single collection time with 95% CIs.
    Supports both absolute temperature/heat index and spatial anomaly.

    When plotting anomaly, applies clean presentation styling:
    - Removes bar edges.
    - Removes top, left, and right axes (spines).
    - Removes y label and y ticks.
    - Uses Figtree font.
    - Moves suptitle to a caption at the bottom.
    - Matches bar label colors to the bar color.
    """
    cfg = _get_col_meta(var_col, variable)
    is_anomaly = bool(cfg["is_anomaly"])

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")

    agg = df.groupby("quintile", observed=False)[var_col].agg(["count", "mean", "std", "sem"])
    means = agg["mean"].values
    ci95 = 1.96 * agg["sem"].values
    counts = agg["count"].values

    indices = np.arange(len(QUINTILE_SHORT_LABELS))

    if is_anomaly:
        ax = fig.add_axes([0.10, 0.18, 0.80, 0.64])

        # Remove top, left, right, and bottom axes
        ax.spines["top"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)

        # Remove y label & ticks
        ax.tick_params(left=False, labelleft=False, bottom=False)
        ax.set_xlim(-0.55, len(QUINTILE_SHORT_LABELS) - 0.45)

        # Zero reference line
        ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2, zorder=1)

        # Bars without edges
        bars = ax.bar(
            indices,
            means,
            width=0.50,
            yerr=ci95,
            capsize=4.5,
            error_kw=dict(ecolor=cfg["color"], lw=1.3, capthick=1.3),
            color=cfg["color"],
            edgecolor="none",
            linewidth=0,
            zorder=3,
        )

        # Value labels matching bar color
        anom_span = max(float(np.max(means + ci95) - min(np.min(means - ci95), 0.0)), 2.0)
        gap_anom = max(0.10, anom_span * 0.025)
        for bar, m, n, ci in zip(bars, means, counts, ci95):
            if m >= 0:
                y_txt = m + ci + gap_anom
                va = "bottom"
            else:
                y_txt = m - ci - gap_anom
                va = "top"
            label_text = f"{m:+.2f} °F\n(N={n:,})"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                y_txt,
                label_text,
                ha="center",
                va=va,
                fontsize=11.0,
                weight="bold",
                color=cfg["color"],
                fontfamily="Figtree",
                zorder=4,
            )

        y_min_bound = min(float(np.min(means - ci95)) - max(0.9, anom_span * 0.22), -3.2)
        y_max_bound = max(float(np.max(means + ci95)) + max(1.3, anom_span * 0.30), 2.6)
        ax.set_ylim(y_min_bound, y_max_bound)

        # Cooling shift annotation
        shift_q = means[-1] - means[0]
        shift_label = "Cooling Shift" if shift_q < 0 else "Shift"
        ax.text(
            0.04,
            0.90,
            f"Quintile 1 → 5 {shift_label}: {shift_q:+.2f} °F",
            transform=ax.transAxes,
            fontsize=12.5,
            weight="bold",
            color=cfg["color"],
            fontfamily="Figtree",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=cfg["light_color"], edgecolor="none", alpha=0.7),
        )

        # Large title at top and left aligned
        fig.text(
            0.10,
            0.94,
            f"{cfg['full_title']} by Tree Canopy Quintile",
            ha="left",
            va="top",
            fontsize=16,
            weight="bold",
            fontfamily="Figtree",
            color="#1F2937",
        )

        # Grayed subtitle remains at the bottom
        fig.text(
            0.50,
            0.035,
            "Error bars represent 95% confidence intervals (±1.96 × SEM) • Reference line at 0 °F (Spatial Mean)",
            ha="center",
            va="center",
            fontsize=11,
            style="italic",
            fontfamily="Figtree",
            color="#6B7280",
        )
    else:
        ax = fig.add_axes([0.14, 0.15, 0.76, 0.70])
        bars = ax.bar(
            indices,
            means,
            width=0.55,
            yerr=ci95,
            capsize=6.0,
            color=cfg["color"],
            edgecolor="#1E293B",
            linewidth=1.2,
            zorder=3,
        )
        val_span = max(float((means + ci95).max() - (means - ci95).min()), 1.0)
        y_floor = float(np.floor((means - ci95).min()) - max(1.5, val_span * 0.18))
        y_ceil = float(np.ceil((means + ci95).max()) + max(1.8, val_span * 0.42))
        ax.set_ylim(y_floor, y_ceil)

        for bar, m, n, ci in zip(bars, means, counts, ci95):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + np.nan_to_num(ci) + max(0.15, val_span * 0.03),
                f"{m:.2f} °F\n(N={n:,})",
                ha="center",
                va="bottom",
                fontsize=10.5,
                weight="bold",
                color="#1F2937",
                fontfamily="Figtree",
                zorder=4,
            )

        shift = float(means[-1] - means[0])
        shift_label = "Cooling Shift" if shift < 0 else "Shift"
        ax.text(
            0.04,
            0.88,
            f"Quintile 1 → 5 {shift_label}: {shift:+.2f} °F",
            transform=ax.transAxes,
            fontsize=12,
            weight="bold",
            color="#1E293B",
            fontfamily="Figtree",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=cfg["light_color"], edgecolor="#9CA3AF", alpha=0.85),
        )
        ax.set_ylabel(cfg["ylabel"], fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
        ax.grid(axis="y", linestyle=":", alpha=0.7, color="#9CA3AF", zorder=0)

        fig.suptitle(f"{cfg['full_title']} by Tree Canopy Quintile", fontsize=17, weight="bold", color="#111827", fontfamily="Figtree", y=0.95)
        fig.text(0.52, 0.89, "Error bars represent 95% confidence intervals (±1.96 × SEM) • NOVA Heat Watch Campaign", ha="center", fontsize=11.5, color="#4B5563", style="italic", fontfamily="Figtree")

    ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=13, weight="bold", color="#1F2937", labelpad=12, fontfamily="Figtree")
    ax.set_xticks(indices)
    ax.set_xticklabels(QUINTILE_LABELS, fontsize=12, color="#1F2937", fontfamily="Figtree")

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
        logger.info("Saved single bar chart: %s", out)

    return fig, ax


def plot_grouped_boxplot(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = DEFAULT_DPI,
    variable: str = "temperature",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Generate a 16:9 grouped boxplot comparing temperature, heat index, or anomaly distributions
    across canopy quintiles for Morning, Afternoon, and Evening.
    """
    if cols is None:
        cols = ["temp_am", "temp_af", "temp_pm"]

    spec = get_variable_spec(variable)
    col_cfgs = [_get_col_meta(c, variable) for c in cols]
    is_anomaly = any(bool(cfg.get("is_anomaly", False)) for cfg in col_cfgs)

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")
    ax = fig.add_axes([0.08, 0.14, 0.88, 0.72])

    n_groups = len(QUINTILE_SHORT_LABELS)
    bar_width = 0.24

    if is_anomaly:
        ax.axhline(0, color="#4B5563", linestyle="--", linewidth=1.4, alpha=0.85, zorder=1)

    whisker_vals = []
    for i, (col, cfg) in enumerate(zip(cols, col_cfgs)):
        data_by_q = [df[df["quintile"] == q][col].values for q in QUINTILE_SHORT_LABELS]

        positions = np.arange(n_groups) + (i - 1) * bar_width

        bp = ax.boxplot(
            data_by_q,
            positions=positions,
            widths=bar_width * 0.82,
            patch_artist=True,
            showfliers=False,  # cleaner presentation on slides
            showmeans=True,
            meanprops=dict(marker="o", markeredgecolor="#111827", markerfacecolor="#FFFFFF", markersize=4.5),
            medianprops=dict(color="#111827", linewidth=1.8),
            boxprops=dict(facecolor=cfg["color"], color="#1E293B", linewidth=1.2, alpha=0.85),
            whiskerprops=dict(color="#1E293B", linewidth=1.2),
            capprops=dict(color="#1E293B", linewidth=1.2),
        )
        for w in bp["whiskers"]:
            whisker_vals.extend(np.asarray(w.get_ydata(), dtype=float).tolist())

    ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=13, weight="bold", color="#1F2937", labelpad=12, fontfamily="Figtree")
    ylabel = f"{spec.display_name} Anomaly ({spec.unit})" if is_anomaly else f"{spec.display_name} ({spec.unit})"
    ax.set_ylabel(ylabel, fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
    ax.set_xticks(np.arange(n_groups))
    ax.set_xticklabels(QUINTILE_LABELS, fontsize=11, color="#1F2937", fontfamily="Figtree")

    finite_whiskers = [v for v in whisker_vals if np.isfinite(v)]
    w_min = float(min(finite_whiskers)) if finite_whiskers else -5.0
    w_max = float(max(finite_whiskers)) if finite_whiskers else 5.0
    if is_anomaly:
        abs_lim = max(abs(w_min), abs(w_max), 6.5)
        y_lim = float(np.ceil(abs_lim) + 1.5)
        ax.set_ylim(-y_lim, y_lim)
    else:
        span = max(w_max - w_min, 5.0)
        ax.set_ylim(float(np.floor(w_min - 2.0)), float(np.ceil(w_max + max(6.5, span * 0.34))))

    ax.grid(axis="y", linestyle=":", alpha=0.7, color="#9CA3AF")

    # Custom legend
    handles = [
        matplotlib.patches.Patch(facecolor=col_cfgs[idx]["color"], edgecolor="#1E293B", label=col_cfgs[idx]["label"])
        for idx in range(len(cols))
    ]
    handles.append(
        matplotlib.lines.Line2D([0], [0], color="#111827", linewidth=1.8, label="Median")
    )
    handles.append(
        matplotlib.lines.Line2D([0], [0], marker="o", color="w", markeredgecolor="#111827", markerfacecolor="#FFFFFF", markersize=5, label="Mean")
    )
    ax.legend(handles=handles, fontsize=11, frameon=True, facecolor="#FFFFFF", edgecolor="#D1D5DB", loc="upper right")

    main_title = (
        f"{spec.display_name} Anomaly Distributions by Tree Canopy Quintile & Collection Time"
        if is_anomaly
        else f"{spec.display_name} Distributions by Tree Canopy Quintile & Collection Time"
    )
    sub_title = (
        "Boxplots display Median, IQR (25th–75th), and 1.5×IQR whiskers • Reference line at 0 °F (Spatial Mean)"
        if is_anomaly
        else "Boxplots display Median, IQR (25th–75th), and 1.5×IQR whiskers • NOVA Heat Watch Campaign"
    )

    fig.suptitle(main_title, fontsize=17, weight="bold", color="#111827", fontfamily="Figtree", y=0.95)
    fig.text(0.52, 0.89, sub_title, ha="center", fontsize=11.5, color="#4B5563", style="italic", fontfamily="Figtree")

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
        logger.info("Saved grouped boxplot: %s", out)

    return fig, ax


def plot_single_boxplot(
    df: pd.DataFrame,
    var_col: str,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = DEFAULT_DPI,
    variable: str = "temperature",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Generate an individual 16:9 boxplot for a single collection time across canopy quintiles.
    Supports both absolute temperature/heat index and spatial anomaly.
    """
    cfg = _get_col_meta(var_col, variable)
    is_anomaly = bool(cfg["is_anomaly"])

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor="#FFFFFF")
    ax = fig.add_axes([0.14, 0.15, 0.76, 0.70])

    data_by_q = [df[df["quintile"] == q][var_col].values for q in QUINTILE_SHORT_LABELS]
    positions = np.arange(len(QUINTILE_SHORT_LABELS))

    if is_anomaly:
        ax.axhline(0, color="#4B5563", linestyle="--", linewidth=1.4, alpha=0.85, zorder=1)

    bp = ax.boxplot(
        data_by_q,
        positions=positions,
        widths=0.48,
        patch_artist=True,
        showfliers=False,
        showmeans=True,
        meanprops=dict(marker="o", markeredgecolor="#111827", markerfacecolor="#FFFFFF", markersize=6.0),
        medianprops=dict(color="#111827", linewidth=2.0),
        boxprops=dict(facecolor=cfg["color"], color="#1E293B", linewidth=1.3, alpha=0.85),
        whiskerprops=dict(color="#1E293B", linewidth=1.3),
        capprops=dict(color="#1E293B", linewidth=1.3),
    )

    medians = [float(np.median(d)) for d in data_by_q]
    means = [float(np.mean(d)) for d in data_by_q]

    # Annotate medians and means above each box
    for pos, m, mn, d in zip(positions, medians, means, data_by_q):
        q75 = np.percentile(d, 75)
        sign = "+" if is_anomaly else ""
        txt = f"Med: {m:{sign}.1f}°\nMean: {mn:{sign}.1f}°"
        ax.text(
            pos,
            q75 + 0.35,
            txt,
            ha="center",
            va="bottom",
            fontsize=10.0,
            weight="bold",
            color="#1F2937",
            fontfamily="Figtree",
        )

    delta_med = medians[-1] - medians[0]
    shift_label = "Median Cooling Shift" if delta_med < 0 else "Median Shift"
    ax.text(
        0.04,
        0.88,
        f"Quintile 1 → 5 {shift_label}: {delta_med:+.2f} °F",
        transform=ax.transAxes,
        fontsize=12,
        weight="bold",
        color="#1E293B",
        fontfamily="Figtree",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=cfg["light_color"], edgecolor="#9CA3AF", alpha=0.85),
    )

    ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=13, weight="bold", color="#1F2937", labelpad=12, fontfamily="Figtree")
    ax.set_ylabel(cfg["ylabel"], fontsize=13, weight="bold", color="#1F2937", labelpad=10, fontfamily="Figtree")
    ax.set_xticks(positions)
    ax.set_xticklabels(QUINTILE_LABELS, fontsize=11, color="#1F2937", fontfamily="Figtree")
    ax.grid(axis="y", linestyle=":", alpha=0.7, color="#9CA3AF")

    # Adjust y limits dynamically from rendered whiskers and box headroom
    whisker_vals = [v for w in bp["whiskers"] for v in np.asarray(w.get_ydata(), dtype=float)]
    w_min = float(np.nanmin(whisker_vals))
    w_max = float(np.nanmax(whisker_vals))
    w_span = max(w_max - w_min, 2.0)
    if is_anomaly:
        y_abs_max = max(abs(w_min), abs(w_max), 6.0)
        y_lim = float(np.ceil(y_abs_max) + 1.8)
        ax.set_ylim(-y_lim, y_lim)
    else:
        ax.set_ylim(float(np.floor(w_min - 1.0)), float(np.ceil(w_max + max(2.2, w_span * 0.28))))

    fig.suptitle(
        f"{cfg['full_title']} Distribution by Canopy Quintile",
        fontsize=17,
        weight="bold",
        color="#111827",
        fontfamily="Figtree",
        y=0.95,
    )
    sub_title = (
        "Boxplots display Median, IQR, and 1.5×IQR whiskers (mean shown as circle) • Reference line at 0 °F (Spatial Mean)"
        if is_anomaly
        else "Boxplots display Median, IQR, and 1.5×IQR whiskers (mean shown as circle) • NOVA Heat Watch Campaign"
    )
    fig.text(
        0.52,
        0.89,
        sub_title,
        ha="center",
        fontsize=11.5,
        color="#4B5563",
        style="italic",
        fontfamily="Figtree",
    )

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
        logger.info("Saved single boxplot: %s", out)

    return fig, ax
