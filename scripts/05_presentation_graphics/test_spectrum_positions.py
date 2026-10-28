import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.patches as patches
from create_quintile_options import (
    load_analysis_dataframe,
    compute_bar_stats,
    draw_bars,
    FONT_FAMILY,
    DPI,
    COLS,
    VARIABLE_CONFIG,
)

def test_font14_legend(df, stats, dot_count, out_name):
    fig = plt.figure(figsize=(13.333, 7.5), facecolor="#FFFFFF", dpi=DPI)
    ax = fig.add_axes([0.08, 0.22, 0.88, 0.56])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, labelleft=False, bottom=False)
    ax.axhline(0, color="#BDC3C7", linewidth=1.2, zorder=2)
    ax.set_xlim(-0.6, 4.6)
    ax.set_ylim(-3.1, 2.8)
    draw_bars(ax, stats)

    # Top Title
    fig.text(
        0.08,
        0.94,
        "Mean Air Temperature Anomaly by Tree Canopy Quintile & Collection Time",
        ha="left",
        va="top",
        fontsize=16,
        weight="bold",
        fontfamily=FONT_FAMILY,
        color="#1F2937",
    )

    # Clean Legend without (AM), (AF), (PM)
    legend_labels = ["Morning", "Afternoon", "Evening"]
    legend_handles = [
        patches.Patch(
            facecolor=VARIABLE_CONFIG[c]["color"],
            edgecolor="none",
            label=lbl,
        )
        for c, lbl in zip(COLS, legend_labels)
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
        columnspacing=2.5,
        handletextpad=0.5,
        prop={"family": FONT_FAMILY, "weight": "bold", "size": 11.5},
    )
    leg.get_frame().set_boxstyle("round,pad=0.45,rounding_size=0.3")

    # Spectrum Bar with font size 14 bold
    dots = " · " * dot_count
    spectrum_str = f"←   LEAST TREE CANOPY   {dots}   MOST TREE CANOPY   →"
    fig.text(
        0.52,
        0.205,
        spectrum_str,
        ha="center",
        va="center",
        fontsize=14,
        weight="bold",
        color="#16A085",
        fontfamily=FONT_FAMILY,
    )

    clean_labels = ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"]
    ax.set_xticks(np.arange(5))
    ax.tick_params(axis="x", pad=26)
    ax.set_xticklabels(clean_labels, fontsize=12, color="#1F2937", fontfamily=FONT_FAMILY)

    # X-axis Title
    fig.text(
        0.52,
        0.090,
        "Tree Canopy Cover Quintiles (Q1 to Q5)",
        ha="center",
        va="center",
        fontsize=12.5,
        weight="bold",
        color="#1F2937",
        fontfamily=FONT_FAMILY,
    )

    # Caption
    fig.text(
        0.50,
        0.035,
        "Quintiles divide Northern Virginia land into 5 equal 20% steps of tree cover • Error bars represent 95% confidence intervals • Baseline at 0 °F (Spatial Mean)",
        ha="center",
        va="center",
        fontsize=10.5,
        style="italic",
        fontfamily=FONT_FAMILY,
        color="#7F8C8D",
    )

    out_path = Path("output/figures/analysis/options") / out_name
    fig.savefig(out_path, dpi=DPI, facecolor="#FFFFFF")
    plt.close(fig)
    print(f"Saved: {out_path}")

def main():
    df = load_analysis_dataframe(Path("output/canopy/grid-canopy.gpkg"))
    stats = compute_bar_stats(df)
    
    test_font14_legend(df, stats, dot_count=36, out_name="test_fs14_dot36.png")
    test_font14_legend(df, stats, dot_count=38, out_name="test_fs14_dot38.png")
    test_font14_legend(df, stats, dot_count=40, out_name="test_fs14_dot40.png")

if __name__ == "__main__":
    main()
