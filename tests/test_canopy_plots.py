"""
tests/test_canopy_plots.py - Unit tests for presentation-grade tree canopy mapping.
"""

from pathlib import Path
import tempfile
import unittest
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uhi.canopy_plots import plot_tree_canopy_map, SLIDE_FIGSIZE


class TestCanopyPlots(unittest.TestCase):
    def setUp(self):
        rows, cols = 5, 5
        data = []
        cell_id = 0
        for r in range(rows):
            for c in range(cols):
                cell_id += 1
                left = 300000.0 + c * 100.0
                right = left + 100.0
                top = 4300000.0 - r * 100.0
                bottom = top - 100.0
                canopy = float((r + c) * 12.5)  # Ranges from 0 to 100
                data.append({
                    "id": cell_id,
                    "row_index": r,
                    "col_index": c,
                    "left": left,
                    "right": right,
                    "top": top,
                    "bottom": bottom,
                    "canopy_pct": canopy,
                    "canopy_m2": canopy * 100.0,
                    "coverage_frac": 1.0,
                })
        self.df = pd.DataFrame(data)

    def test_plot_tree_canopy_map_continuous(self):
        """Verify continuous mode renders correctly with proper 16:9 canvas dimensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_canopy_cont.png"
            fig, ax = plot_tree_canopy_map(
                grid_data=self.df,
                boundary_path=None,
                output_path=out_file,
                mode="continuous",
                dpi=100,
            )

            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)
            self.assertAlmostEqual(fig.get_size_inches()[0], SLIDE_FIGSIZE[0], places=2)
            self.assertAlmostEqual(fig.get_size_inches()[1], SLIDE_FIGSIZE[1], places=2)
            plt.close("all")

    def test_plot_tree_canopy_map_discrete(self):
        """Verify discrete 5-tier mode renders correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_canopy_disc.png"
            fig, ax = plot_tree_canopy_map(
                grid_data=self.df,
                boundary_path=None,
                output_path=out_file,
                mode="discrete",
                dpi=100,
            )

            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)
            plt.close("all")

    def test_plot_tree_canopy_map_invalid_mode(self):
        """Verify ValueError is raised for invalid modes."""
        with self.assertRaises(ValueError):
            plot_tree_canopy_map(grid_data=self.df, mode="invalid_mode")

    def test_plot_tree_canopy_map_file_not_found(self):
        """Verify FileNotFoundError is raised for nonexistent input path."""
        with self.assertRaises(FileNotFoundError):
            plot_tree_canopy_map(grid_data="nonexistent_canopy_file.gpkg")


if __name__ == "__main__":
    unittest.main()

