"""Raster I/O and data models for Urban Heat Island (UHI) temperature surfaces."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import re

import numpy as np
import rasterio
from rasterio.crs import CRS
from affine import Affine

PERIODS: Dict[str, str] = {
    "am": "Morning (AM)",
    "af": "Afternoon (AF)",
    "pm": "Evening (PM)",
}

PERIOD_ORDER: List[str] = ["am", "af", "pm"]


@dataclass
class UHIRaster:
    """Represents a georeferenced Urban Heat Island temperature surface."""
    period: str
    label: str
    data: np.ndarray
    extent: Tuple[float, float, float, float]  # (left, right, bottom, top)
    crs: CRS
    transform: Affine
    source_path: Optional[Path] = None

    @property
    def spatial_mean(self) -> float:
        """Calculate the spatial mean temperature across valid pixels."""
        return float(np.nanmean(self.data))

    @property
    def anomaly(self) -> np.ndarray:
        """Calculate spatial anomaly: T - mean(T)."""
        return self.data - self.spatial_mean

    def clip(self, boundary: Union[str, Path, object]) -> "UHIRaster":
        """Clip raster to a polygon boundary geometry (GeoPackage, Shapefile, or GeoDataFrame)."""
        return clip_uhi_raster(self, boundary)

    def summary(self) -> Dict[str, float]:
        """Compute key summary statistics for the temperature surface."""
        valid_vals = self.data[np.isfinite(self.data)]
        if valid_vals.size == 0:
            return {
                "min": np.nan,
                "p2": np.nan,
                "mean": np.nan,
                "p98": np.nan,
                "max": np.nan,
                "valid_pct": 0.0,
            }

        return {
            "min": float(np.min(valid_vals)),
            "p2": float(np.percentile(valid_vals, 2)),
            "mean": float(np.mean(valid_vals)),
            "p98": float(np.percentile(valid_vals, 98)),
            "max": float(np.max(valid_vals)),
            "valid_pct": float(valid_vals.size / self.data.size * 100.0),
        }


def clip_uhi_raster(
    raster: UHIRaster,
    boundary: Union[str, Path, object],
) -> UHIRaster:
    """
    Clip a UHIRaster to the given polygon boundary (GeoPackage, Shapefile, or GeoDataFrame).
    Pixels outside the boundary are set to NaN.
    """
    import geopandas as gpd
    from rasterio.features import geometry_mask

    if isinstance(boundary, (str, Path)):
        gdf = gpd.read_file(boundary)
    else:
        gdf = boundary

    # Ensure CRS matches raster
    if gdf.crs != raster.crs:
        gdf = gdf.to_crs(raster.crs)

    inside_mask = geometry_mask(
        gdf.geometry,
        out_shape=raster.data.shape,
        transform=raster.transform,
        invert=True,
    )
    new_data = raster.data.copy()
    new_data[~inside_mask] = np.nan

    return UHIRaster(
        period=raster.period,
        label=raster.label,
        data=new_data,
        extent=raster.extent,
        crs=raster.crs,
        transform=raster.transform,
        source_path=raster.source_path,
    )


def extract_period(filename: str) -> str:
    """Extract period identifier ('am', 'af', 'pm') from a filename."""
    lower_name = filename.lower()
    for p in PERIOD_ORDER:
        # Match _am-, _af-, _pm- or am/af/pm surrounded by non-alphanumerics
        if re.search(rf"(?:^|[_\W]){p}(?:[_\W]|$)", lower_name):
            return p
    # Fallback to direct substring search
    for p in PERIOD_ORDER:
        if p in lower_name:
            return p
    # Check natural language names
    if "morning" in lower_name:
        return "am"
    if "afternoon" in lower_name:
        return "af"
    if "evening" in lower_name:
        return "pm"
    raise ValueError(f"Could not determine period ('am', 'af', 'pm') from filename: {filename}")


def load_uhi_raster(
    path: Union[str, Path],
    boundary: Optional[Union[str, Path, object]] = None,
) -> UHIRaster:
    """Load a single UHI GeoTIFF into a UHIRaster instance, optionally clipping to boundary."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Raster file not found: {path}")

    period = extract_period(path.name)
    label = PERIODS.get(period, period.upper())

    with rasterio.open(path) as src:
        band = src.read(1).astype(np.float32)
        nodata = src.nodata
        if nodata is not None:
            band[band == nodata] = np.nan
        # Ensure any infs are treated as NaN
        band[~np.isfinite(band)] = np.nan

        bounds = src.bounds
        extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
        crs = src.crs
        transform = src.transform

    raster = UHIRaster(
        period=period,
        label=label,
        data=band,
        extent=extent,
        crs=crs,
        transform=transform,
        source_path=path,
    )

    if boundary is not None:
        raster = raster.clip(boundary)

    return raster


def load_uhi_rasters(
    folder: Union[str, Path],
    pattern: str = "*.tif",
    boundary: Optional[Union[str, Path, object]] = None,
) -> List[UHIRaster]:
    """
    Load all UHI rasters matching pattern in folder, sorted chronologically (am, af, pm).
    Optionally clips each raster to a polygon boundary.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder}")

    files = list(folder.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' in {folder}")

    rasters: List[UHIRaster] = []
    for f in files:
        try:
            rasters.append(load_uhi_raster(f, boundary=boundary))
        except ValueError:
            # Skip tif files that do not match period naming
            continue

    if not rasters:
        raise ValueError(f"No valid UHI rasters found in {folder} with periods 'am', 'af', 'pm'")

    # Sort by defined period order
    rasters.sort(key=lambda r: PERIOD_ORDER.index(r.period) if r.period in PERIOD_ORDER else 99)

    # Check CRS consistency
    first_crs = rasters[0].crs
    for r in rasters[1:]:
        if r.crs != first_crs:
            import warnings
            warnings.warn(f"CRS mismatch detected: {r.period} ({r.crs}) vs {rasters[0].period} ({first_crs})")

    return rasters

