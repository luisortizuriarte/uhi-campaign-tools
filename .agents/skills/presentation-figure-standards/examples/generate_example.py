"""
Example Demonstrating Presentation Figure Design Standards
=========================================================
Generates a demonstration figure using `figure_template.py`.
"""

import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(script_dir))

from figure_template import plot_presentation_grouped_bar, PALETTE

def main():
    categories = [
        "0–20%\n(Q1)",
        "20–40%\n(Q2)",
        "40–60%\n(Q3)",
        "60–80%\n(Q4)",
        "80–100%\n(Q5)",
    ]

    series_data = {
        "am": {
            "label": "Morning (AM)",
            "color": PALETTE["morning"],
            "means": [1.27, 0.47, -0.11, -0.68, -1.35],
            "errors": [0.03, 0.02, 0.02, 0.02, 0.03],
        },
        "af": {
            "label": "Afternoon (AF)",
            "color": PALETTE["afternoon"],
            "means": [1.14, 0.53, 0.03, -0.58, -1.65],
            "errors": [0.04, 0.03, 0.03, 0.03, 0.04],
        },
        "pm": {
            "label": "Evening (PM)",
            "color": PALETTE["evening"],
            "means": [1.72, 1.10, 0.46, -0.72, -2.46],
            "errors": [0.05, 0.04, 0.03, 0.04, 0.05],
        },
    }

    out_file = Path(__file__).resolve().parent / "example_presentation_chart.png"

    fig = plot_presentation_grouped_bar(
        categories=categories,
        series_data=series_data,
        title="Mean Air Temperature Anomaly by Tree Canopy Quintile & Collection Time",
        caption="Error bars represent 95% confidence intervals of the mean • Reference line at 0 °F (Spatial Mean) • Northern Virginia Heat Watch Campaign",
        xlabel="Tree Canopy Cover Quintile",
        output_path=str(out_file),
        ylim=(-3.1, 2.5),
    )
    print(f"Example figure created successfully at: {out_file}")

if __name__ == "__main__":
    main()

