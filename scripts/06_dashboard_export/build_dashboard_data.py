#!/usr/bin/env python3
"""
build_dashboard_data.py - Extract and package NOVA UHI grid data for the web dashboard.

Produces:
1. web_dashboard/data/manifest.json - Metadata, grid layout, color LUTs, and statistics.
2. web_dashboard/data/grid_data.bin - Compact binary packed arrays for all 362x399 cells.
3. web_dashboard/data/mercator_map.bin - Pre-computed (523x479) pixel-to-grid index for instant canvas render.
4. web_dashboard/data/counties.geojson - Simplified WGS84 boundary vectors for overlay.
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


import json
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pyogrio
import pyproj

def build_data():
    base_dir = PROJECT_ROOT
    out_dir = base_dir / "web_dashboard" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    hotspots_path = base_dir / "output" / "hotspots" / "hotspots.gpkg"
    counties_path = base_dir / "input_data" / "county_boundaries" / "novauhi_counties.gpkg"

    print(f"Reading {hotspots_path}...")
    df = pyogrio.read_dataframe(hotspots_path, read_geometry=False)

    nrows = int(df['row_index'].max() + 1)  # 362
    ncols = int(df['col_index'].max() + 1)  # 399
    total_cells = nrows * ncols

    xmin = float(df['left'].min())
    xmax = float(df['right'].max())
    ymin = float(df['bottom'].min())
    ymax = float(df['top'].max())
    cell_size = 100.0

    print(f"Grid dimensions: {nrows} rows x {ncols} cols ({total_cells} cells)")
    print(f"UTM Bounds: [{xmin}, {ymin}, {xmax}, {ymax}]")

    # Order cells by row_index, col_index
    df = df.sort_values(by=['row_index', 'col_index']).reset_index(drop=True)

    inside = (df['coverage_frac'].values > 0).astype(np.uint8)

    # Helper for Int16 packed temperatures (deg F * 10, nodata = -32768)
    def pack_temp(col_name):
        arr = np.full(total_cells, -32768, dtype=np.int16)
        vals = df[col_name].values
        valid = inside.astype(bool) & np.isfinite(vals)
        arr[valid] = np.round(vals[valid] * 10.0).astype(np.int16)
        return arr

    # Helper for Int16 packed anomalies (deg F * 100, nodata = -32768)
    def pack_anom(col_name):
        arr = np.full(total_cells, -32768, dtype=np.int16)
        vals = df[col_name].values
        valid = inside.astype(bool) & np.isfinite(vals)
        arr[valid] = np.round(vals[valid] * 100.0).astype(np.int16)
        return arr

    # Helper for Uint8 packed canopy (0-100, nodata = 255)
    def pack_canopy():
        arr = np.full(total_cells, 255, dtype=np.uint8)
        vals = df['canopy_pct'].values
        valid = inside.astype(bool) & np.isfinite(vals)
        arr[valid] = np.clip(np.round(vals[valid]), 0, 100).astype(np.uint8)
        return arr

    # Helper for Uint8 spot (0=Not Sig, 1=Cold, 2=Hot, 255=NoData)
    def pack_spot(col_name):
        arr = np.full(total_cells, 255, dtype=np.uint8)
        is_hot = df[f'is_hot_{col_name}'].values == 1
        is_cold = df[f'is_cold_{col_name}'].values == 1
        v_ins = inside.astype(bool)
        arr[v_ins] = 0
        arr[v_ins & is_cold] = 1
        arr[v_ins & is_hot] = 2
        return arr

    # Helper for Uint8 persistence
    # 0=Not Sig, 1=Mixed, 2=Cold 1x, 3=Cold 2x, 4=Cold 3x, 5=Hot 1x, 6=Hot 2x, 7=Hot 3x, 255=NoData
    def pack_persistence():
        arr = np.full(total_cells, 255, dtype=np.uint8)
        v_ins = inside.astype(bool)
        arr[v_ins] = 0
        n_hot = df['n_hot_periods'].values
        n_cold = df['n_cold_periods'].values

        mixed = v_ins & (n_hot > 0) & (n_cold > 0)
        arr[mixed] = 1

        for k in (1, 2, 3):
            c_mask = v_ins & (n_cold == k) & (n_hot == 0)
            arr[c_mask] = 1 + k  # 2, 3, 4

        for k in (1, 2, 3):
            h_mask = v_ins & (n_hot == k) & (n_cold == 0)
            arr[h_mask] = 4 + k  # 5, 6, 7
        return arr

    # Helper for Int8 Gi* z-score (z * 10, clamped [-127, 127], nodata = -128)
    def pack_zscore(period):
        arr = np.full(total_cells, -128, dtype=np.int8)
        vals = df[f'gi_z_{period}'].values
        valid = inside.astype(bool) & np.isfinite(vals)
        arr[valid] = np.clip(np.round(vals[valid] * 10.0), -127, 127).astype(np.int8)
        return arr

    print("Packing grid attribute arrays...")
    t_am = pack_temp('temp_am')
    t_af = pack_temp('temp_af')
    t_pm = pack_temp('temp_pm')

    a_am = pack_anom('anom_am')
    a_af = pack_anom('anom_af')
    a_pm = pack_anom('anom_pm')

    canopy = pack_canopy()

    spot_am = pack_spot('am')
    spot_af = pack_spot('af')
    spot_pm = pack_spot('pm')

    pers = pack_persistence()

    z_am = pack_zscore('am')
    z_af = pack_zscore('af')
    z_pm = pack_zscore('pm')

    bin_path = out_dir / "grid_data.bin"
    with open(bin_path, "wb") as f:
        inside.tofile(f)
        t_am.tofile(f)
        t_af.tofile(f)
        t_pm.tofile(f)
        a_am.tofile(f)
        a_af.tofile(f)
        a_pm.tofile(f)
        canopy.tofile(f)
        spot_am.tofile(f)
        spot_af.tofile(f)
        spot_pm.tofile(f)
        pers.tofile(f)
        z_am.tofile(f)
        z_af.tofile(f)
        z_pm.tofile(f)

    print(f"Exported binary grid data to {bin_path} ({bin_path.stat().st_size / 1024:.1f} KB)")

    # -------------------------------------------------------------
    # Compute Web Mercator (EPSG:3857) pixel-to-cell index map
    # -------------------------------------------------------------
    print("Computing Web Mercator projection lookup mapping...")
    trans_utm_to_3857 = pyproj.Transformer.from_crs('EPSG:32618', 'EPSG:3857', always_xy=True)
    trans_3857_to_utm = pyproj.Transformer.from_crs('EPSG:3857', 'EPSG:32618', always_xy=True)
    trans_3857_to_wgs = pyproj.Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True)

    corners_utm = [(xmin, ymin), (xmax, ymin), (xmin, ymax), (xmax, ymax)]
    m_corners = [trans_utm_to_3857.transform(x, y) for x, y in corners_utm]
    m_xs = [p[0] for p in m_corners]
    m_ys = [p[1] for p in m_corners]

    m_xmin, m_xmax = min(m_xs), max(m_xs)
    m_ymin, m_ymax = min(m_ys), max(m_ys)

    sw_lon, sw_lat = trans_3857_to_wgs.transform(m_xmin, m_ymin)
    ne_lon, ne_lat = trans_3857_to_wgs.transform(m_xmax, m_ymax)

    m_w = 523
    m_h = 479

    dx = (m_xmax - m_xmin) / m_w
    dy = (m_ymax - m_ymin) / m_h

    xs = m_xmin + (np.arange(m_w) + 0.5) * dx
    ys = m_ymax - (np.arange(m_h) + 0.5) * dy

    X, Y = np.meshgrid(xs, ys)
    UX, UY = trans_3857_to_utm.transform(X, Y)

    C = np.floor((UX - xmin) / cell_size).astype(np.int32)
    R = np.floor((ymax - UY) / cell_size).astype(np.int32)

    valid = (C >= 0) & (C < ncols) & (R >= 0) & (R < nrows)
    raw_indices = R * ncols + C

    flat_idx = np.full(m_w * m_h, -1, dtype=np.int32)
    flat_idx[valid.flatten()] = raw_indices[valid]

    # Check whether the mapped cell is also an inside ROI cell
    valid_mapped = flat_idx >= 0
    mapped_inside = np.zeros(m_w * m_h, dtype=bool)
    mapped_inside[valid_mapped] = (inside[flat_idx[valid_mapped]] == 1)
    flat_idx[~mapped_inside] = -1

    mercator_bin_path = out_dir / "mercator_map.bin"
    flat_idx.tofile(mercator_bin_path)
    print(f"Exported Mercator index map to {mercator_bin_path} ({mercator_bin_path.stat().st_size / 1024:.1f} KB)")

    # Color LUT helper
    def get_lut(cmap_name, n=256):
        cmap = plt.get_cmap(cmap_name)
        vals = cmap(np.linspace(0, 1, n))[:, :3] * 255
        return vals.astype(int).tolist()

    manifest = {
        "grid": {
            "nrows": nrows,
            "ncols": ncols,
            "total_cells": total_cells,
            "cell_size": cell_size,
            "crs": "EPSG:32618",
            "utm_bounds": [xmin, ymin, xmax, ymax],
        },
        "mercator": {
            "width": m_w,
            "height": m_h,
            "m_bounds": [m_xmin, m_ymin, m_xmax, m_ymax],
            "overlay_bounds": [[sw_lat, sw_lon], [ne_lat, ne_lon]],
            "center": [(sw_lat + ne_lat) / 2.0, (sw_lon + ne_lon) / 2.0]
        },
        "offsets": {
            "inside": 0,
            "temp_am": total_cells,
            "temp_af": total_cells + total_cells * 2,
            "temp_pm": total_cells + total_cells * 4,
            "anom_am": total_cells + total_cells * 6,
            "anom_af": total_cells + total_cells * 8,
            "anom_pm": total_cells + total_cells * 10,
            "canopy": total_cells + total_cells * 12,
            "spot_am": total_cells + total_cells * 12 + total_cells,
            "spot_af": total_cells + total_cells * 12 + total_cells * 2,
            "spot_pm": total_cells + total_cells * 12 + total_cells * 3,
            "pers": total_cells + total_cells * 12 + total_cells * 4,
            "z_am": total_cells + total_cells * 12 + total_cells * 5,
            "z_af": total_cells + total_cells * 12 + total_cells * 6,
            "z_pm": total_cells + total_cells * 12 + total_cells * 7,
        },
        "stats": {
            "temp_am": {"min": 75.0, "max": 85.5, "p2": 77.2, "p98": 83.6, "mean": 80.6},
            "temp_af": {"min": 87.5, "max": 101.5, "p2": 91.7, "p98": 97.9, "mean": 95.3},
            "temp_pm": {"min": 86.0, "max": 100.5, "p2": 87.9, "p98": 96.3, "mean": 93.1},
            "anom": {"limit": 6.0, "p2": -4.0, "p98": 3.0},
            "canopy": {"min": 0.0, "max": 100.0, "mean": 50.2},
            "zscore": {"min": -8.0, "max": 8.0}
        },
        "colors": {
            "temp_lut": get_lut("YlOrRd", 256),
            "anom_lut": get_lut("Spectral_r", 256),
            "canopy_lut": get_lut("YlGn", 256),
            "zscore_lut": get_lut("RdBu_r", 256),
            "spots": {
                "0": [229, 231, 235],  # #E5E7EB Not Significant
                "1": [41, 128, 185],   # #2980B9 Cold Spot
                "2": [231, 76, 60]     # #E74C3C Hot Spot
            },
            "persistence": {
                "0": [229, 231, 235],  # #E5E7EB Not Significant
                "1": [203, 213, 225],  # #CBD5E1 Mixed Shift
                "2": [212, 230, 241],  # #D4E6F1 Cold Spot (1 Time)
                "3": [133, 193, 233],  # #85C1E9 Cold Spot (2 Times)
                "4": [41, 128, 185],   # #2980B9 Cold Spot (All 3 Times)
                "5": [250, 219, 216],  # #FADBD8 Hot Spot (1 Time)
                "6": [241, 148, 138],  # #F1948A Hot Spot (2 Times)
                "7": [231, 76, 60]     # #E74C3C Hot Spot (All 3 Times)
            }
        },
        "labels": {
            "persistence": [
                "Not Significant",
                "Mixed Shift (Warm & Cool)",
                "Cold Spot (1 Period)",
                "Cold Spot (2 Periods)",
                "Cold Spot (All 3 Periods - Refuge)",
                "Hot Spot (1 Period)",
                "Hot Spot (2 Periods)",
                "Hot Spot (All 3 Periods - Severe Island)"
            ],
            "spots": [
                "Not Significant",
                "Cold Spot (p ≤ 0.05)",
                "Hot Spot (p ≤ 0.05)"
            ]
        }
    }

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Exported manifest to {manifest_path} ({manifest_path.stat().st_size / 1024:.1f} KB)")

    # Simplified counties GeoJSON
    if counties_path.is_file():
        print(f"Reading and simplifying {counties_path}...")
        b = gpd.read_file(counties_path)
        b_4326 = b.to_crs(epsg=4326)
        b_4326_simple = b_4326.copy()
        b_4326_simple['geometry'] = b_4326.geometry.simplify(0.0005, preserve_topology=True)
        b_4326_simple = b_4326_simple[['NAME', 'geometry']]
        geojson_path = out_dir / "counties.geojson"
        b_4326_simple.to_file(geojson_path, driver="GeoJSON")
        print(f"Exported simplified boundaries to {geojson_path} ({geojson_path.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    build_data()

