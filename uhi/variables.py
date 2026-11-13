"""Variable metadata and pipeline path configuration for temperature and heat index workflows."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class VariableSpec:
    """Configuration defining labels, input rasters, and non-destructive output paths for an analysis variable."""

    key: str
    display_name: str
    short_name: str
    abbr: str
    unit: str
    input_rasters: Dict[str, str]
    clipped_rasters: Dict[str, Path]
    grid_input_gpkg: Path
    grid_output_gpkg: Path
    hotspots_dir: Path
    locations_dir: Path
    figures_dir: Path
    value_subdir: str
    value_file_prefix: str
    anomaly_file_prefix: str
    school_bar_prefix: str
    school_scatter_filename: str

    @property
    def raster_glob(self) -> str:
        """Glob matching raw input GeoTIFF files in input_data/maps."""
        return "predicted_temperature_surface_*-whole.tif" if self.key == "temperature" else "full-*-hi.tif"


VARIABLES: Dict[str, VariableSpec] = {
    "temperature": VariableSpec(
        key="temperature",
        display_name="Air Temperature",
        short_name="Temperature",
        abbr="Temp",
        unit="°F",
        input_rasters={
            "am": "predicted_temperature_surface_am-whole.tif",
            "af": "predicted_temperature_surface_af-whole.tif",
            "pm": "predicted_temperature_surface_pm-whole.tif",
        },
        clipped_rasters={
            "am": Path("output/temperature/morning_clipped.tif"),
            "af": Path("output/temperature/afternoon_clipped.tif"),
            "pm": Path("output/temperature/evening_clipped.tif"),
        },
        grid_input_gpkg=Path("output/canopy/grid-canopy.gpkg"),
        grid_output_gpkg=Path("output/temperature/grid-temp.gpkg"),
        hotspots_dir=Path("output/temperature/hotspots"),
        locations_dir=Path("output/temperature/locations"),
        figures_dir=Path("output/figures/air_temperature"),
        value_subdir="temperature",
        value_file_prefix="uhi_temperature",
        anomaly_file_prefix="uhi_anomaly",
        school_bar_prefix="school_temps_hottest_to_coldest",
        school_scatter_filename="school_canopy_vs_temperature_anomaly.png",
    ),
    "heat_index": VariableSpec(
        key="heat_index",
        display_name="Heat Index",
        short_name="Heat Index",
        abbr="HI",
        unit="°F",
        input_rasters={
            "am": "full-am-hi.tif",
            "af": "full-af-hi.tif",
            "pm": "full-pm-hi.tif",
        },
        clipped_rasters={
            "am": Path("output/heat_index/morning_hi_clipped.tif"),
            "af": Path("output/heat_index/afternoon_hi_clipped.tif"),
            "pm": Path("output/heat_index/evening_hi_clipped.tif"),
        },
        grid_input_gpkg=Path("output/canopy/grid-canopy.gpkg"),
        grid_output_gpkg=Path("output/heat_index/grid-hi.gpkg"),
        hotspots_dir=Path("output/heat_index/hotspots"),
        locations_dir=Path("output/heat_index/locations"),
        figures_dir=Path("output/figures/heat_index"),
        value_subdir="heat_index",
        value_file_prefix="uhi_heat_index",
        anomaly_file_prefix="uhi_hi_anomaly",
        school_bar_prefix="school_hi_hottest_to_coldest",
        school_scatter_filename="school_canopy_vs_hi_anomaly.png",
    ),
}


def get_variable_spec(variable: str = "temperature") -> VariableSpec:
    """Return the VariableSpec for 'temperature' or 'heat_index'."""
    key = variable.lower().strip()
    if key not in VARIABLES:
        raise ValueError(f"Unknown variable '{variable}'. Expected one of: {list(VARIABLES.keys())}")
    return VARIABLES[key]


def resolve_clipped_rasters(
    spec: VariableSpec,
    maps_dir: Path = Path("input_data/maps"),
    boundary_path: Optional[Path] = Path("input_data/county_boundaries/novauhi_counties.gpkg"),
) -> Dict[str, Path]:
    """
    Return paths to boundary-clipped GeoTIFFs for a variable, generating and caching
    them from the raw rasters if they do not yet exist.
    """
    from uhi.io import export_clipped_geotiff

    if all(p.is_file() for p in spec.clipped_rasters.values()):
        return dict(spec.clipped_rasters)

    raw_paths = {p: Path(maps_dir) / fname for p, fname in spec.input_rasters.items()}
    if boundary_path is None or not Path(boundary_path).is_file():
        return raw_paths

    resolved: Dict[str, Path] = {}
    for p, raw_p in raw_paths.items():
        clipped_p = spec.clipped_rasters[p]
        if not clipped_p.is_file():
            export_clipped_geotiff(raw_p, clipped_p, boundary_path)
        resolved[p] = clipped_p
    return resolved

