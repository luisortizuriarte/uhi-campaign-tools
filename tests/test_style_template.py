"""
Unit tests for uhi.style_template module.
"""

import unittest
from pathlib import Path
import tempfile
import matplotlib.pyplot as plt
from uhi.style_template import (
    plot_presentation_grouped_bar,
    PALETTE,
    SLIDE_FIGSIZE,
    SLIDE_DPI,
)

class TestStyleTemplate(unittest.TestCase):
    def test_palette_and_constants(self):
        self.assertEqual(SLIDE_FIGSIZE, (13.333, 7.5))
        self.assertEqual(SLIDE_DPI, 300)
        self.assertEqual(PALETTE["morning"], "#2980B9")
        self.assertEqual(PALETTE["afternoon"], "#F39C12")
        self.assertEqual(PALETTE["evening"], "#E74C3C")

    def test_plot_presentation_grouped_bar(self):
        categories = ["A", "B"]
        series_data = {
            "am": {
                "label": "Morning",
                "color": PALETTE["morning"],
                "means": [1.0, -1.0],
                "errors": [0.1, 0.1],
            },
            "af": {
                "label": "Afternoon",
                "color": PALETTE["afternoon"],
                "means": [0.5, -0.5],
                "errors": [0.05, 0.05],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_out.png"
            fig = plot_presentation_grouped_bar(
                categories=categories,
                series_data=series_data,
                title="Test Title",
                caption="Test Caption",
                output_path=str(out_path),
            )
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_path.is_file())
            plt.close(fig)

if __name__ == "__main__":
    unittest.main()

