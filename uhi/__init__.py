"""UHI Field Measurements Mapping Package for NOVA Campaign."""

import os
import sys
from pathlib import Path

# Configure GDAL_DATA and PROJ_LIB if running in a conda/mamba environment on Windows
prefix = Path(sys.prefix)
gdal_data_cand = prefix / "Library" / "share" / "gdal"
proj_lib_cand = prefix / "Library" / "share" / "proj"

if "GDAL_DATA" not in os.environ and gdal_data_cand.is_dir():
    os.environ["GDAL_DATA"] = str(gdal_data_cand)

if "PROJ_LIB" not in os.environ and proj_lib_cand.is_dir():
    os.environ["PROJ_LIB"] = str(proj_lib_cand)

__all__ = [
    "io",
    "plotting",
    "canopy",
    "canopy_plots",
    "zonal",
    "analysis",
    "style_template",
    "locations",
    "school_analysis",
    "hotspots",
    "hotspot_plots",
]

