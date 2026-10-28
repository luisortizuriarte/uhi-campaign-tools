"""
Presentation Figure Design Standards Template
=============================================
Reusable template and utility functions for generating publication-quality,
presentation-ready 16:9 widescreen charts adhering to the NOVA Campaign
de-cluttered design standards.
"""

from typing import Dict, List, Optional, Tuple, Sequence
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# -----------------------------------------------------------------------------
# DESIGN SYSTEM TOKENS
# -----------------------------------------------------------------------------
SLIDE_FIGSIZE: Tuple[float, float] = (13.333, 7.5)  # 16:9 widescreen in inches
SLIDE_DPI: int = 300

# Color Palette
PALETTE = {
    "morning": "#2980B9",    # Strong Blue (AM)
    "afternoon": "#F39C12",  # Warm Amber / Orange (AF)
    "evening": "#E74C3C",    # Warm Coral Red (PM)
    "neutral_dark": "#1F2937",  # Main title & category text
    "neutral_gray": "#7F8C8D",  # Subtitles, captions, metadata
    "baseline": "#BDC3C7",      # Zero reference horizontal line
    "legend_bg": "#ECF0F1",     # Legend container fill
    "canvas_bg": "#FFFFFF",     # White slide canvas
}

# Typography Standards
FONT_FAMILY = "Figtree"
FALLBACK_FONTS = ["Figtree", "DejaVu Sans", "Arial", "sans-serif"]


def configure_presentation_style():
    """Apply global matplotlib style defaults for Figtree and clean rendering."""
    plt.rcParams["font.family"] = FALLBACK_FONTS
    plt.rcParams["text.color"] = PALETTE["neutral_dark"]
    plt.rcParams["axes.labelcolor"] = PALETTE["neutral_dark"]
    plt.rcParams["xtick.color"] = PALETTE["neutral_dark"]
    plt.rcParams["ytick.color"] = PALETTE["neutral_dark"]
    plt.rcParams["figure.facecolor"] = PALETTE["canvas_bg"]
    plt.rcParams["axes.facecolor"] = PALETTE["canvas_bg"]


def plot_presentation_grouped_bar(
    categories: Sequence[str],
    series_data: Dict[str, Dict[str, Sequence[float]]],
    title: str,
    caption: str,
    xlabel: Optional[str] = None,
    output_path: Optional[str] = None,
    value_fmt: str = "+.2f",
    unit_str: str = "°",
    ylim: Optional[Tuple[float, float]] = None,
    baseline_val: float = 0.0,
    dpi: int = SLIDE_DPI,
) -> plt.Figure:
    """
    Generate a 16:9 presentation grouped bar chart following the de-cluttered design standards.

    Parameters
    ----------
    categories : Sequence[str]
        Labels for each category / group along the x-axis (e.g. Quintiles).
    series_data : Dict[str, Dict[str, Sequence[float]]]
        Dictionary mapping series key to a dict with:
          - "label": str (display name in legend)
          - "color": str (hex color)
          - "means": Sequence[float] (values for each category)
          - "errors": Optional[Sequence[float]] (error bar sizes, e.g. 95% CI)
    title : str
        Main title, left-aligned at top of canvas.
    caption : str
        Subtle footer caption at bottom center of canvas.
    xlabel : Optional[str]
        Label for the x-axis.
    output_path : Optional[str]
        File path to save the figure if provided.
    value_fmt : str
        Format string for direct numerical bar labels.
    unit_str : str
        Unit suffix for value labels (e.g. "°" or "%").
    ylim : Optional[Tuple[float, float]]
        Custom (ymin, ymax) limits. If None, automatically computed.
    baseline_val : float
        Reference line value (default: 0.0).
    dpi : int
        Figure DPI (default: 300).

    Returns
    -------
    matplotlib.figure.Figure
    """
    configure_presentation_style()

    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=dpi, facecolor=PALETTE["canvas_bg"])

    # Geometry: [left, bottom, width, height]
    # Leaves room for title (y=0.94), lowered legend (y=0.76-0.80), and bottom caption (y=0.035)
    ax = fig.add_axes([0.08, 0.16, 0.88, 0.62])

    # De-clutter: Remove top, left, right, bottom outer spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Remove Y-axis ticks and labels completely; keep clean X categories without ticks
    ax.tick_params(left=False, labelleft=False, bottom=False)

    n_groups = len(categories)
    indices = np.arange(n_groups)
    n_series = len(series_data)
    bar_width = 0.72 / max(n_series, 1)

    # Draw zero reference baseline
    ax.axhline(baseline_val, color=PALETTE["baseline"], linestyle="-", linewidth=1.2, zorder=1)

    all_vals = []
    legend_handles = []

    for i, (key, s_info) in enumerate(series_data.items()):
        color = s_info.get("color", PALETTE["morning"])
        label = s_info.get("label", key)
        means = np.asarray(s_info["means"])
        errors = np.asarray(s_info.get("errors", np.zeros_like(means)))

        offset = (i - (n_series - 1) / 2.0) * bar_width
        pos = indices + offset

        # Plot bars: no border/edge, solid fill
        bars = ax.bar(
            pos,
            means,
            bar_width,
            yerr=errors,
            capsize=3.5,
            error_kw=dict(ecolor=color, lw=1.3, capthick=1.3),
            color=color,
            edgecolor="none",
            linewidth=0,
            label=label,
            zorder=3,
        )

        legend_handles.append(
            mpatches.Patch(facecolor=color, edgecolor="none", label=label)
        )

        # Direct numerical data labels matching bar fill color
        for bar, val, err in zip(bars, means, errors):
            if np.isnan(val):
                continue
            is_pos = val >= baseline_val
            err_offset = err if not np.isnan(err) else 0.0

            # Compute label position beyond bar/error cap
            val_offset = 0.12 if is_pos else -0.16
            y_pos = (val + err_offset + val_offset) if is_pos else (val - err_offset + val_offset)
            va = "bottom" if is_pos else "top"

            sign = "+" if val > 0 else ""
            txt = f"{sign}{val:.2f}{unit_str}"

            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                y_pos,
                txt,
                ha="center",
                va=va,
                fontsize=10.5,
                weight="bold",
                color=color,
                fontfamily=FONT_FAMILY,
                zorder=4,
            )

            all_vals.append(val + err_offset)
            all_vals.append(val - err_offset)

    # X-axis configuration
    ax.set_xlim(-0.55, n_groups - 0.45)
    ax.set_xticks(indices)
    ax.set_xticklabels(categories, fontsize=12, color=PALETTE["neutral_dark"], fontfamily=FONT_FAMILY)

    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13, weight="bold", color=PALETTE["neutral_dark"], labelpad=12, fontfamily=FONT_FAMILY)

    # Automatic Y-limits with padding if not provided
    if ylim:
        ax.set_ylim(ylim)
    elif len(all_vals) > 0:
        min_v = np.nanmin(all_vals)
        max_v = np.nanmax(all_vals)
        pad_top = max(0.6, abs(max_v) * 0.25)
        pad_bot = max(0.6, abs(min_v) * 0.25)
        ax.set_ylim(min_v - pad_bot, max_v + pad_top)

    # Top Left-Aligned Title
    fig.text(
        0.08,
        0.94,
        title,
        ha="left",
        va="top",
        fontsize=16,
        weight="bold",
        fontfamily=FONT_FAMILY,
        color=PALETTE["neutral_dark"],
    )

    # Lowered Horizontal Legend: Centered, square markers, rounded light gray container
    leg = ax.legend(
        handles=legend_handles,
        ncols=n_series,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.98),
        frameon=True,
        facecolor=PALETTE["legend_bg"],
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

    # Explanatory Caption at Bottom Center
    fig.text(
        0.50,
        0.035,
        caption,
        ha="center",
        va="center",
        fontsize=10.5,
        color=PALETTE["neutral_gray"],
        fontfamily=FONT_FAMILY,
        style="italic",
    )

    if output_path:
        fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches=None)

    return fig

