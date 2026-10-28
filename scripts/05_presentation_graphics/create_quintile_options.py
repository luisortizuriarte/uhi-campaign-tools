#!/usr/bin/env python3
"""
create_quintile_options.py - Generate 3 distinct design options for explaining
tree canopy quintiles to a general audience on the grouped anomaly bar chart.
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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from uhi.analysis import load_analysis_dataframe, VARIABLE_CONFIG

# Configuration & Styling Standards
SLIDE_FIGSIZE = (13.333, 7.5)
DPI = 300
FONT_FAMILY = "Figtree"
FALLBACK_FONTS = ["Figtree", "DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["font.family"] = FALLBACK_FONTS

# Data constants
COLS = ["anom_am", "anom_af", "anom_pm"]
BAR_WIDTH = 0.24


def compute_bar_stats(df):
    """Compute means and 95% confidence intervals per quintile per period."""
    stats = {}
    for col in COLS:
        agg = df.groupby("quintile", observed=False)[col].agg(["mean", "sem"])
        means = agg["mean"].values
        ci95 = 1.96 * agg["sem"].values
        stats[col] = (means, ci95)
    return stats


def setup_base_figure(
    ax_rect=[0.08, 0.16, 0.88, 0.62],
    title_text="Mean Air Temperature Anomaly by Tree Canopy Quintile & Collection Time",
    y_lim=(-3.1, 2.5),
    transparent: bool = False,
):
    """Initialize standard 16:9 figure with Tufte layout and bespoke legend."""
    facecolor = "none" if transparent else "#FFFFFF"
    fig = plt.figure(figsize=SLIDE_FIGSIZE, dpi=DPI, facecolor=facecolor)
    if transparent:
        fig.patch.set_alpha(0.0)
    ax = fig.add_axes(ax_rect)
    if transparent:
        ax.set_facecolor("none")
        ax.patch.set_alpha(0.0)

    # De-cluttering (Tufte style)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, labelleft=False, bottom=False)

    # Category limits and reference line
    ax.set_xlim(-0.55, 4.45)
    ax.set_ylim(y_lim[0], y_lim[1])
    ax.axhline(0, color="#BDC3C7", linestyle="-", linewidth=1.2, zorder=1)

    # Title at top left
    fig.text(
        0.08,
        0.94,
        title_text,
        ha="left",
        va="top",
        fontsize=16,
        weight="bold",
        fontfamily=FONT_FAMILY,
        color="#1F2937",
    )

    # Legend lowered below title, centered at top, 3 columns, square markers (no AM/AF/PM)
    clean_legend_names = {"anom_am": "Morning", "anom_af": "Afternoon", "anom_pm": "Evening"}
    legend_handles = [
        patches.Patch(
            facecolor=VARIABLE_CONFIG[c]["color"],
            edgecolor="none",
            label=clean_legend_names[c],
        )
        for c in COLS
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
        borderpad=0.5,
        columnspacing=2.2,
        handletextpad=0.5,
        prop={"family": FONT_FAMILY, "weight": "bold", "size": 11},
    )
    leg.get_frame().set_boxstyle("round,pad=0.45,rounding_size=0.3")

    return fig, ax


def draw_bars(ax, stats):
    """Draw the grouped bars with error bars and colored value labels."""
    indices = np.arange(5)
    for i, col in enumerate(COLS):
        cfg = VARIABLE_CONFIG[col]
        means, ci95 = stats[col]
        pos = indices + (i - 1) * BAR_WIDTH

        bars = ax.bar(
            pos,
            means,
            BAR_WIDTH,
            yerr=ci95,
            capsize=3.5,
            error_kw=dict(ecolor=cfg["color"], lw=1.3, capthick=1.3),
            color=cfg["color"],
            edgecolor="none",
            linewidth=0,
            label=cfg["label"],
            zorder=3,
        )

        for bar, m, ci in zip(bars, means, ci95):
            if m >= 0:
                y_txt = m + ci + 0.10
                va = "bottom"
            else:
                y_txt = m - ci - 0.12
                va = "top"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                y_txt,
                f"{m:+.2f}°",
                ha="center",
                va=va,
                fontsize=10.5,
                weight="bold",
                color=cfg["color"],
                fontfamily=FONT_FAMILY,
                zorder=4,
            )


# -----------------------------------------------------------------------------
# OPTION 1: Directional Canopy Spectrum Guide (Bottom Axis Banner)
# -----------------------------------------------------------------------------
def make_option_1(df, out_path: Path, transparent: bool = False):
    """
    Option 1: Directional Spectrum Guide.
    Adds plain-English landscape descriptors to category ticks and places an elegant
    directional spectrum guide bar beneath the axis with arrow indicators.
    """
    stats = compute_bar_stats(df)
    # Give comfortable headroom and dedicate space between plot and labels
    fig, ax = setup_base_figure(
        ax_rect=[0.08, 0.22, 0.88, 0.56],
        y_lim=(-3.1, 2.8),
        transparent=transparent,
    )
    draw_bars(ax, stats)

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
        fontfamily=FONT_FAMILY,
    )

    # 2. Clean quintile labels on ticks without qualifiers
    clean_labels = [
        "0–20%",
        "20–40%",
        "40–60%",
        "60–80%",
        "80–100%",
    ]
    ax.set_xticks(np.arange(5))
    ax.tick_params(axis="x", pad=26)
    ax.set_xticklabels(clean_labels, fontsize=12, color="#1F2937", fontfamily=FONT_FAMILY)

    # 3. X-axis Title
    fig.text(
        0.529,
        0.090,
        "Tree Canopy Cover Quintiles (Q1 to Q5)",
        ha="center",
        va="center",
        fontsize=12.5,
        weight="bold",
        color="#1F2937",
        fontfamily=FONT_FAMILY,
    )

    # 4. Bottom caption
    fig.text(
        0.50,
        0.030,
        "Quintiles divide Northern Virginia land into 5 equal 20% steps of tree cover • Error bars represent 95% confidence intervals • Baseline at 0 °F (Spatial Mean)",
        ha="center",
        va="center",
        fontsize=10.5,
        style="italic",
        fontfamily=FONT_FAMILY,
        color="#7F8C8D",
    )

    if transparent:
        fig.savefig(out_path, dpi=DPI, transparent=True)
    else:
        fig.savefig(out_path, dpi=DPI, facecolor="#FFFFFF")
    plt.close(fig)


# -----------------------------------------------------------------------------
# OPTION 2: Floating Explanatory Callout Card
# -----------------------------------------------------------------------------
def make_option_2(df, out_path: Path):
    """
    Option 2: Floating Explanatory Callout Card.
    Utilizes the spacious upper-right whitespace (above Q4 & Q5) to provide a clear,
    audience-friendly card defining quintiles and their real-world meanings.
    """
    stats = compute_bar_stats(df)
    fig, ax = setup_base_figure(ax_rect=[0.08, 0.16, 0.88, 0.62], y_lim=(-3.1, 2.9))
    draw_bars(ax, stats)

    # Category labels with archetypes
    opt2_labels = [
        "0–20%\n(Q1: Paved / Urban)",
        "20–40%\n(Q2: Low Canopy)",
        "40–60%\n(Q3: Moderate)",
        "60–80%\n(Q4: Wooded)",
        "80–100%\n(Q5: Dense Forest)",
    ]
    ax.set_xticks(np.arange(5))
    ax.set_xticklabels(opt2_labels, fontsize=11.5, color="#1F2937", fontfamily=FONT_FAMILY)
    ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=12.5, weight="bold", color="#1F2937", labelpad=12, fontfamily=FONT_FAMILY)

    # Explanatory Card in upper-right quadrant
    # Positioned cleanly below legend level and comfortably above baseline
    card_text = (
        "Understanding Tree Canopy Quintiles\n"
        "• Quintiles divide the region into 5 equal 20% tiers\n"
        "  to compare areas from least to most shaded.\n"
        "• Q1 (0–20%): Heavily built, paved & commercial cores\n"
        "• Q3 (40–60%): Typical established suburban neighborhoods\n"
        "• Q5 (80–100%): Preserved parks, stream valleys & forests\n"
        "• Key Finding: Tree-dense areas are up to 4.2 °F cooler"
    )
    ax.text(
        3.68,
        0.30,
        card_text,
        ha="center",
        va="bottom",
        fontsize=9.2,
        color="#1F2937",
        fontfamily=FONT_FAMILY,
        linespacing=1.35,
        bbox=dict(
            boxstyle="round,pad=0.55,rounding_size=0.35",
            facecolor="#ECF0F1",
            edgecolor="#CBD5E1",
            linewidth=1.0,
            alpha=0.98,
        ),
        zorder=5,
    )

    # Bottom caption
    fig.text(
        0.50,
        0.035,
        "Error bars represent 95% confidence intervals of the mean • Reference line at 0 °F (Spatial Mean) • Northern Virginia Heat Watch Campaign",
        ha="center",
        va="center",
        fontsize=10.5,
        style="italic",
        fontfamily=FONT_FAMILY,
        color="#7F8C8D",
    )

    fig.savefig(out_path, dpi=DPI, facecolor="#FFFFFF")
    plt.close(fig)


# -----------------------------------------------------------------------------
# OPTION 3: Two-Zone Microclimate Banners & Transition Marker
# -----------------------------------------------------------------------------
def make_option_3(df, out_path: Path):
    """
    Option 3: Two-Zone Microclimate Banners & Neutral Baseline Transition Marker.
    Visually separates the 'Heat Vulnerability Zone' (Q1-Q2) from the 'Cooling Refuge Zone' (Q4-Q5),
    with an annotated indicator arrow at Q3 marking the 50% neutral temperature threshold.
    """
    stats = compute_bar_stats(df)
    # Set y limits with comfortable headroom for zone banners
    fig, ax = setup_base_figure(ax_rect=[0.08, 0.16, 0.88, 0.62], y_lim=(-3.1, 3.2))
    draw_bars(ax, stats)

    opt3_labels = [
        "0–20%\n(Q1: Urban Core)",
        "20–40%\n(Q2: Low Shade)",
        "40–60%\n(Q3: Moderate)",
        "60–80%\n(Q4: Wooded)",
        "80–100%\n(Q5: Forested)",
    ]
    ax.set_xticks(np.arange(5))
    ax.set_xticklabels(opt3_labels, fontsize=11.5, color="#1F2937", fontfamily=FONT_FAMILY)
    ax.set_xlabel("Tree Canopy Cover Quintile", fontsize=12.5, weight="bold", color="#1F2937", labelpad=12, fontfamily=FONT_FAMILY)

    # 1. Warm Deficit Zone Banner (Q1-Q2: x = 0.15, y = 2.65)
    ax.text(
        0.18,
        2.65,
        "HEAT VULNERABILITY ZONE (<40% Canopy)\nConsistently Warmer than Average (+0.5° to +1.7°F)",
        ha="center",
        va="center",
        fontsize=8.8,
        weight="bold",
        color="#9A3412",  # Warm dark amber
        fontfamily=FONT_FAMILY,
        linespacing=1.2,
        bbox=dict(
            boxstyle="round,pad=0.45,rounding_size=0.3",
            facecolor="#FFEDD5",  # Soft warm amber tint
            edgecolor="#FDBA74",
            linewidth=1.0,
            alpha=0.95,
        ),
        zorder=5,
    )

    # 2. Cool Refuge Zone Banner (Q4-Q5: x = 3.75, y = 2.65)
    ax.text(
        3.75,
        2.65,
        "URBAN COOLING REFUGE (>60% Canopy)\nConsistently Cooler than Average (-0.6° to -2.5°F)",
        ha="center",
        va="center",
        fontsize=8.8,
        weight="bold",
        color="#065F46",  # Forest dark green
        fontfamily=FONT_FAMILY,
        linespacing=1.2,
        bbox=dict(
            boxstyle="round,pad=0.45,rounding_size=0.3",
            facecolor="#D1FAE5",  # Soft emerald mint tint
            edgecolor="#6EE7B7",
            linewidth=1.0,
            alpha=0.95,
        ),
        zorder=5,
    )

    # 3. Transition Marker at Q3 (x = 2.0)
    # Positioned between top of Q3 bars (+0.46) and legend bottom
    ax.annotate(
        "Transition Threshold (~50% Canopy)\nOffsets urban heat to campaign average",
        xy=(2.0, 0.48),
        xytext=(2.0, 1.15),
        ha="center",
        va="bottom",
        fontsize=8.8,
        weight="bold",
        color="#374151",
        fontfamily=FONT_FAMILY,
        arrowprops=dict(
            arrowstyle="->",
            color="#4B5563",
            lw=1.2,
            mutation_scale=12,
        ),
        bbox=dict(
            boxstyle="round,pad=0.35,rounding_size=0.25",
            facecolor="#F3F4F6",
            edgecolor="#D1D5DB",
            linewidth=0.8,
        ),
        zorder=6,
    )

    # Bottom caption
    fig.text(
        0.50,
        0.035,
        "Quintiles segment tree canopy into 5 equal 20% steps • Error bars represent 95% confidence intervals • Reference line at 0 °F (Spatial Mean)",
        ha="center",
        va="center",
        fontsize=10.5,
        style="italic",
        fontfamily=FONT_FAMILY,
        color="#7F8C8D",
    )

    fig.savefig(out_path, dpi=DPI, facecolor="#FFFFFF")
    plt.close(fig)


def main():
    grid_gpkg = Path("output/canopy/grid-canopy.gpkg")
    print(f"Loading data from {grid_gpkg}...")
    df = load_analysis_dataframe(grid_gpkg)

    out_dir = Path("output/figures/analysis/options")
    out_dir.mkdir(parents=True, exist_ok=True)

    opt1_path = out_dir / "barchart_canopy_quintiles_anom_grouped_opt1_spectrum.png"
    main_grouped_path = Path("output/figures/analysis/barchart_canopy_quintiles_anom_grouped.png")
    main_grouped_trans_path = Path("output/figures/analysis/barchart_canopy_quintiles_anom_grouped_transparent.png")
    opt2_path = out_dir / "barchart_canopy_quintiles_anom_grouped_opt2_card.png"
    opt3_path = out_dir / "barchart_canopy_quintiles_anom_grouped_opt3_zones.png"

    print("Generating Option 1 (Redone): Directional Spectrum Guide...")
    make_option_1(df, opt1_path)
    make_option_1(df, main_grouped_path)
    make_option_1(df, main_grouped_trans_path, transparent=True)
    print(f"  -> Saved: {opt1_path}")
    print(f"  -> Updated: {main_grouped_path}")
    print(f"  -> Generated: {main_grouped_trans_path}")

    print("Generating Option 2: Floating Explanatory Callout Card...")
    make_option_2(df, opt2_path)
    print(f"  -> Saved: {opt2_path}")

    print("Generating Option 3: Two-Zone Microclimate Banners & Transition Marker...")
    make_option_3(df, opt3_path)
    print(f"  -> Saved: {opt3_path}")

    print("All 3 options generated successfully!")


if __name__ == "__main__":
    main()
