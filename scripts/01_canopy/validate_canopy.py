"""
validate_canopy.py - Validates the aggregated canopy grid against exact vector overlays.
Selects sample 1km x 1km blocks across jurisdictions and boundaries, computes exact
Shapely vector intersections, and checks error statistics.
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


import time
import geopandas as gpd
import numpy as np
import pyogrio
import shapely
from shapely.geometry import box

import uhi
from uhi.canopy import CANOPY_SOURCES


def main():
    print("=" * 65)
    print("VALIDATING TREE CANOPY AGGREGATION RESULTS")
    print("=" * 65)

    # 1. Load generated canopy grid
    gpkg_path = "output/canopy/grid-canopy.gpkg"
    print(f"Loading {gpkg_path} ...")
    grid = pyogrio.read_dataframe(gpkg_path)
    print(f"Loaded {len(grid):,} grid cells.")

    # 2. Basic integrity checks
    assert "canopy_pct" in grid.columns, "Missing canopy_pct column"
    assert "canopy_m2" in grid.columns, "Missing canopy_m2 column"
    assert "covered_m2" in grid.columns, "Missing covered_m2 column"
    assert "coverage_frac" in grid.columns, "Missing coverage_frac column"

    valid_mask = grid["coverage_frac"] > 0
    null_mask = grid["coverage_frac"] == 0

    print("\n--- Field Integrity ---")
    print(f"Cells inside study area (coverage_frac > 0): {valid_mask.sum():,}")
    print(f"Cells outside study area (coverage_frac = 0): {null_mask.sum():,}")
    print(f"NULL canopy_pct in uncovered cells: {grid.loc[null_mask, 'canopy_pct'].isna().all()}")

    valid_pcts = grid.loc[valid_mask, "canopy_pct"]
    assert (valid_pcts >= 0.0).all() and (valid_pcts <= 100.0).all(), "canopy_pct out of range [0, 100]"
    print(f"Range of canopy_pct: {valid_pcts.min():.2f}% to {valid_pcts.max():.2f}%")

    # 3. Sample block validation against exact vector calculations
    # Test blocks of 1km x 1km (10x10 cells = 100 cells each)
    test_blocks = [
        {"name": "Fairfax Suburban (Reston/Herndon)", "bbox": (290000, 4310000, 2910000, 4311000)},
        {"name": "Arlington Urban Core", "bbox": (318000, 4304000, 3190000, 4305000)},
        {"name": "Alexandria West End", "bbox": (315000, 4296000, 3160000, 4297000)},
        {"name": "Fairfax-Arlington Border", "bbox": (314000, 4305000, 3150000, 4306000)},
    ]

    print("\n--- Detailed Vector Sampling Validation (1km x 1km blocks) ---")
    study_gdf = pyogrio.read_dataframe("input_data/county_boundaries/novauhi_counties.gpkg")

    all_diffs = []
    for block in test_blocks:
        b_name = block["name"]
        b_box = box(*block["bbox"])
        print(f"\nEvaluating block: {b_name}...")

        # Find cells intersecting the block
        cells = grid[
            (grid["left"] >= block["bbox"][0])
            & (grid["right"] <= block["bbox"][2])
            & (grid["bottom"] >= block["bbox"][1])
            & (grid["top"] <= block["bbox"][3])
        ].copy()

        if len(cells) == 0:
            print("  No cells found in block!")
            continue

        # Load canopy vector features in this block for all sources
        block_canopy_polys = []
        for src_name, src_path, _ in CANOPY_SOURCES:
            src_crs = pyogrio.read_info(src_path)["crs"]
            # Reproject block bbox to source CRS
            from pyproj import Transformer
            tr = Transformer.from_crs("EPSG:32618", src_crs, always_xy=True)
            src_bbox = tr.transform_bounds(*block["bbox"])

            polys = pyogrio.read_dataframe(src_path, bbox=src_bbox)
            if len(polys) > 0:
                polys = polys.to_crs(32618)
                polys = polys[polys.intersects(b_box)]
                if len(polys) > 0:
                    valid_geoms = shapely.make_valid(polys.geometry.values)
                    block_canopy_polys.extend(valid_geoms)

        # Vector union of canopy in block
        if block_canopy_polys:
            canopy_union = shapely.union_all(block_canopy_polys)
        else:
            canopy_union = Polygon()

        # Intersect with study area
        study_union = shapely.union_all(study_gdf.geometry.values)
        canopy_in_study = shapely.intersection(canopy_union, study_union)

        diffs = []
        for idx, row in cells.iterrows():
            c_geom = row.geometry
            c_study = shapely.intersection(c_geom, study_union)
            c_study_area = c_study.area
            if c_study_area > 0:
                c_canopy = shapely.intersection(c_study, canopy_in_study)
                exact_pct = (c_canopy.area / c_study_area) * 100.0
                raster_pct = row["canopy_pct"]
                diff = abs(raster_pct - exact_pct)
                diffs.append(diff)
                all_diffs.append(diff)

        if diffs:
            print(f"  Sampled {len(diffs)} cells: Mean Absolute Error = {np.mean(diffs):.2f} pp, Max Error = {np.max(diffs):.2f} pp")

    if all_diffs:
        overall_mae = np.mean(all_diffs)
        print("\n" + "=" * 65)
        print(f"OVERALL VECTOR VALIDATION ERROR (MAE): {overall_mae:.2f} percentage points")
        print("=" * 65)
        assert overall_mae < 1.0, f"Error exceeds threshold (MAE = {overall_mae:.2f} pp >= 1.0 pp)"
        print("VERIFICATION CHECK PASSED: Rasterized canopy accuracy is well within <1 percentage point tolerance.")


if __name__ == "__main__":
    main()

