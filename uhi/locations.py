"""
School Locations Processing Module for NOVA Campaign
====================================================
Combines school location datasets from Alexandria (ALX), Arlington (ARL),
and Fairfax (FFX) into a unified GeoPackage layer of school points.

Building polygons from ALX and ARL are converted to their geometric centroids.
Fairfax points are preserved. All layers are reprojected to EPSG:32618.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_ALX_PATH = Path("input_data/locations/alx_School_Boundary/School_Boundary.shp")
DEFAULT_ARL_PATH = Path("input_data/locations/arl-school-Building_Polygons/Building_Polygons.shp")
DEFAULT_FFX_PATH = Path("input_data/locations/ffx_School_Facilities_4781285296506604441/School_Facilities.shp")
DEFAULT_OUTPUT_GPKG = Path("output/locations/school_locs.gpkg")
DEFAULT_CRS = "EPSG:32618"


def _infer_alx_school_type(name: str) -> str:
    """Infer standardized school type code from Alexandria school name."""
    name_lower = str(name).lower()
    if "elementary" in name_lower:
        return "ES"
    elif "middle" in name_lower:
        return "MS"
    elif "high" in name_lower or "ninth grade" in name_lower:
        return "HS"
    elif "k-8" in name_lower:
        return "K-8"
    return "Other"


def load_alx_schools(
    shp_path: Union[str, Path] = DEFAULT_ALX_PATH,
    target_crs: str = DEFAULT_CRS,
) -> gpd.GeoDataFrame:
    """
    Load Alexandria school building polygons, calculate centroids, and standardize attributes.

    Parameters
    ----------
    shp_path : Union[str, Path]
        Path to Alexandria school boundary shapefile.
    target_crs : str
        Target CRS string (default EPSG:32618).

    Returns
    -------
    gpd.GeoDataFrame
        Standardized GeoDataFrame of school point centroids.
    """
    path = Path(shp_path)
    if not path.is_file():
        raise FileNotFoundError(f"Alexandria school shapefile not found at {path}")

    logger.info("Loading Alexandria schools from %s ...", path)
    gdf = gpd.read_file(path)

    # Reproject to target CRS before computing centroid for true Euclidean distance
    gdf_proj = gdf.to_crs(target_crs)
    centroids = gdf_proj.geometry.centroid

    out_gdf = gdf_proj.copy()
    if "FID" in out_gdf.columns:
        out_gdf = out_gdf.rename(columns={"FID": "orig_fid"})
    out_gdf["geometry"] = centroids
    out_gdf["school_name"] = gdf["NAME"].astype(str)
    out_gdf["jurisdiction"] = "Alexandria"
    out_gdf["county_code"] = "ALX"
    out_gdf["school_type"] = gdf["NAME"].apply(_infer_alx_school_type)
    out_gdf["address"] = gdf["ADDRESS"].astype(str)
    out_gdf["orig_geom"] = "Polygon"
    out_gdf["orig_id"] = gdf["FID"].astype(str)
    if "ADDRESS" in out_gdf.columns:
        out_gdf = out_gdf.drop(columns=["ADDRESS"])

    logger.info("Loaded %d Alexandria school centroids.", len(out_gdf))
    return out_gdf


def load_arl_schools(
    shp_path: Union[str, Path] = DEFAULT_ARL_PATH,
    target_crs: str = DEFAULT_CRS,
) -> gpd.GeoDataFrame:
    """
    Load Arlington school building polygons, calculate centroids, and standardize attributes.

    Parameters
    ----------
    shp_path : Union[str, Path]
        Path to Arlington school building polygons shapefile.
    target_crs : str
        Target CRS string (default EPSG:32618).

    Returns
    -------
    gpd.GeoDataFrame
        Standardized GeoDataFrame of school point centroids.
    """
    path = Path(shp_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arlington school shapefile not found at {path}")

    logger.info("Loading Arlington schools from %s ...", path)
    gdf = gpd.read_file(path)

    gdf_proj = gdf.to_crs(target_crs)
    centroids = gdf_proj.geometry.centroid

    out_gdf = gdf_proj.copy()
    out_gdf["geometry"] = centroids
    # Use CM_Label if available, fallback to Building_L
    names = gdf["CM_Label"].fillna(gdf["Building_L"]).astype(str)
    out_gdf["school_name"] = names
    out_gdf["jurisdiction"] = "Arlington"
    out_gdf["county_code"] = "ARL"
    out_gdf["school_type"] = gdf["SCHOOL"].astype(str)
    out_gdf["address"] = None
    out_gdf["orig_geom"] = "Polygon"
    out_gdf["orig_id"] = gdf["OBJECTID"].astype(str)

    logger.info("Loaded %d Arlington school centroids.", len(out_gdf))
    return out_gdf


def load_ffx_schools(
    shp_path: Union[str, Path] = DEFAULT_FFX_PATH,
    target_crs: str = DEFAULT_CRS,
) -> gpd.GeoDataFrame:
    """
    Load Fairfax school facilities points and standardize attributes.

    Parameters
    ----------
    shp_path : Union[str, Path]
        Path to Fairfax school facilities shapefile.
    target_crs : str
        Target CRS string (default EPSG:32618).

    Returns
    -------
    gpd.GeoDataFrame
        Standardized GeoDataFrame of school points.
    """
    path = Path(shp_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fairfax school shapefile not found at {path}")

    logger.info("Loading Fairfax schools from %s ...", path)
    gdf = gpd.read_file(path)

    gdf_proj = gdf.to_crs(target_crs)

    out_gdf = gdf_proj.copy()
    out_gdf["school_name"] = gdf["SCHOOL_NAM"].astype(str)
    out_gdf["jurisdiction"] = "Fairfax"
    out_gdf["county_code"] = "FFX"
    out_gdf["school_type"] = gdf["SCHOOL_TYP"].astype(str)
    out_gdf["address"] = gdf["ADDRESS"].astype(str)
    out_gdf["orig_geom"] = "Point"
    out_gdf["orig_id"] = gdf["GlobalID"].astype(str)
    if "ADDRESS" in out_gdf.columns:
        out_gdf = out_gdf.drop(columns=["ADDRESS"])

    logger.info("Loaded %d Fairfax school points.", len(out_gdf))
    return out_gdf


def combine_school_locations(
    alx_path: Union[str, Path] = DEFAULT_ALX_PATH,
    arl_path: Union[str, Path] = DEFAULT_ARL_PATH,
    ffx_path: Union[str, Path] = DEFAULT_FFX_PATH,
    target_crs: str = DEFAULT_CRS,
    output_gpkg: Optional[Union[str, Path]] = DEFAULT_OUTPUT_GPKG,
    layer_name: str = "school_locs",
    secondary_output: Optional[Union[str, Path]] = Path("school_locs.gpkg"),
) -> gpd.GeoDataFrame:
    """
    Combine Alexandria, Arlington, and Fairfax school datasets into a unified GeoPackage layer.

    Parameters
    ----------
    alx_path : Union[str, Path]
        Path to Alexandria school boundary shapefile.
    arl_path : Union[str, Path]
        Path to Arlington school building polygons shapefile.
    ffx_path : Union[str, Path]
        Path to Fairfax school facilities shapefile.
    target_crs : str
        Target CRS string (default EPSG:32618).
    output_gpkg : Optional[Union[str, Path]]
        Destination GeoPackage path (default: output/locations/school_locs.gpkg).
    layer_name : str
        Layer name inside GeoPackage (default: 'school_locs').
    secondary_output : Optional[Union[str, Path]]
        Additional copy path (e.g. root 'school_locs.gpkg').

    Returns
    -------
    gpd.GeoDataFrame
        Combined GeoDataFrame of all school locations.
    """
    alx_gdf = load_alx_schools(alx_path, target_crs=target_crs)
    arl_gdf = load_arl_schools(arl_path, target_crs=target_crs)
    ffx_gdf = load_ffx_schools(ffx_path, target_crs=target_crs)

    # Standard priority column order
    std_cols = [
        "school_name",
        "jurisdiction",
        "county_code",
        "school_type",
        "address",
        "orig_geom",
        "orig_id",
        "geometry",
    ]

    # Combine all GeoDataFrames
    combined_df = pd.concat([alx_gdf, arl_gdf, ffx_gdf], ignore_index=True)

    # Reorder columns: standard columns first, followed by source-specific columns
    other_cols = [c for c in combined_df.columns if c not in std_cols]
    final_cols = std_cols + other_cols
    combined_df = combined_df[final_cols]

    combined_gdf = gpd.GeoDataFrame(combined_df, geometry="geometry", crs=target_crs)

    # Deduplicate column names case-insensitively for SQLite/GeoPackage compatibility
    seen_lower = set()
    cols_to_keep = []
    for c in combined_gdf.columns:
        cl = c.lower()
        if cl not in seen_lower:
            seen_lower.add(cl)
            cols_to_keep.append(c)
        else:
            logger.debug("Dropping case-insensitive duplicate column '%s'", c)
    combined_gdf = combined_gdf[cols_to_keep]

    # Remove datetime timezone or format issues if any for GPKG serialization
    for col in combined_gdf.columns:
        if pd.api.types.is_datetime64_any_dtype(combined_gdf[col]):
            combined_gdf[col] = combined_gdf[col].astype(str)

    logger.info("Combined total of %d schools across 3 jurisdictions.", len(combined_gdf))
    for jurisdiction, count in combined_gdf["jurisdiction"].value_counts().items():
        logger.info("  - %s: %d schools", jurisdiction, count)

    if output_gpkg:
        out_path = Path(output_gpkg)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Saving combined school locations to %s (layer='%s') ...", out_path, layer_name)
        combined_gdf.to_file(out_path, layer=layer_name, driver="GPKG")
        logger.info("Successfully saved %s", out_path)

    if secondary_output:
        sec_path = Path(secondary_output)
        sec_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Saving secondary copy to %s (layer='%s') ...", sec_path, layer_name)
        combined_gdf.to_file(sec_path, layer=layer_name, driver="GPKG")
        logger.info("Successfully saved %s", sec_path)

    return combined_gdf
