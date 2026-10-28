# Northern Virginia Urban Heat Island Data Dictionary

This document details the data schemas, coordinate reference systems (CRS), units, and field definitions across all input datasets and generated analytical products.

---

## 1. Spatial Coordinate Reference Systems (CRS)

| Dataset Type | Primary CRS | EPSG | Description |
| :--- | :--- | :--- | :--- |
| **Analytical Grid & Canopy** | UTM Zone 18N | `EPSG:32618` | Metric Cartesian coordinates ($100\text{m} \times 100\text{m}$ cells) |
| **Continuous Model Rasters** | UTM Zone 18N | `EPSG:32618` | 10m/100m continuous GeoTIFF surfaces |
| **County Boundaries** | WGS 84 / UTM 18N | `EPSG:4326` / `EPSG:32618` | Standard latitude/longitude and projected polygons |
| **Web Dashboard Layers** | Web Mercator / WGS 84 | `EPSG:3857` / `EPSG:4326` | Leaflet.js standard web mapping projection |

---

## 2. Master Analytical Product: `output/hotspots/hotspots.gpkg`

Contains the complete $362 \times 399$ grid ($144,438$ total features) covering the Northern Virginia study region (Fairfax County, Arlington County, and the City of Alexandria).

| Field Name | Type | Units / Values | Description |
| :--- | :--- | :--- | :--- |
| `row_index` | Integer | $0 \dots 361$ | Grid row coordinate (North to South) |
| `col_index` | Integer | $0 \dots 398$ | Grid column coordinate (West to East) |
| `left` | Float | Meters | Minimum Easting (UTM Zone 18N) |
| `bottom` | Float | Meters | Minimum Northing (UTM Zone 18N) |
| `right` | Float | Meters | Maximum Easting (UTM Zone 18N) |
| `top` | Float | Meters | Maximum Northing (UTM Zone 18N) |
| `canopy_m2` | Float | $m^2$ | Area of tree canopy within cell boundaries |
| `covered_m2` | Float | $m^2$ | Total cell area within study region ($0 \dots 10,000$) |
| `coverage_frac`| Float | $[0.0, 1.0]$ | Fraction of cell inside study area ($1.0 = \text{100\% inside}$) |
| `canopy_pct` | Float | Percentage $[0.0, 100.0]$ | Tree canopy percentage ($\text{canopy\_m2} / \text{covered\_m2} \times 100$) |
| `temp_am` | Float | °F | Zonal mean Morning air temperature (6:00–7:00 AM) |
| `temp_af` | Float | °F | Zonal mean Afternoon air temperature (3:00–4:00 PM) |
| `temp_pm` | Float | °F | Zonal mean Evening air temperature (7:00–8:00 PM) |
| `anom_am` | Float | °F | Morning spatial anomaly ($T_{\text{am}} - \overline{T}_{\text{am, regional}}$) |
| `anom_af` | Float | °F | Afternoon spatial anomaly ($T_{\text{af}} - \overline{T}_{\text{af, regional}}$) |
| `anom_pm` | Float | °F | Evening spatial anomaly ($T_{\text{pm}} - \overline{T}_{\text{pm, regional}}$) |
| `gi_am` | Float | Real | Morning Getis-Ord local spatial autocorrelation statistic |
| `gi_af` | Float | Real | Afternoon Getis-Ord local spatial autocorrelation statistic |
| `gi_pm` | Float | Real | Evening Getis-Ord local spatial autocorrelation statistic |
| `z_am` | Float | Standard deviations | Morning standardized z-score |
| `z_af` | Float | Standard deviations | Afternoon standardized z-score |
| `z_pm` | Float | Standard deviations | Evening standardized z-score |
| `p_am` | Float | $[0.0, 1.0]$ | Morning two-tailed p-value |
| `p_af` | Float | $[0.0, 1.0]$ | Afternoon two-tailed p-value |
| `p_pm` | Float | $[0.0, 1.0]$ | Evening two-tailed p-value |
| `spot_am` | String | Categorical | Morning cluster (`Hot Spot 99%`, `Not Significant`, `Cold Spot 99%`, etc.) |
| `spot_af` | String | Categorical | Afternoon cluster classification |
| `spot_pm` | String | Categorical | Evening cluster classification |
| `pers_level` | String | Categorical | Diurnal persistence (`Persistent Hot`, `Persistent Cold`, `Variable`) |
| `geom` | Polygon | Coordinates in EPSG:32618 | $100\text{m} \times 100\text{m}$ cell boundary box geometry |

---

## 3. Intermediate Product: `output/canopy/grid-canopy.gpkg`

Generated in Stage 1 & 2 before spatial autocorrelation modeling. Contains identical geometry and canopy columns (`canopy_m2`, `covered_m2`, `coverage_frac`, `canopy_pct`) plus the zonal temperatures (`temp_am`, `temp_af`, `temp_pm`) and anomalies (`anom_am`, `anom_af`, `anom_pm`).

---

## 4. Facility Vulnerability Product: `output/locations/school_heat_exposure.csv`

Contains heat exposure metrics for public schools and community facilities across Northern Virginia.

| Column | Type | Description |
| :--- | :--- | :--- |
| `school_name` | String | Official name of educational institution |
| `jurisdiction`| String | County or city (`Fairfax`, `Arlington`, `Alexandria`) |
| `latitude` | Float | WGS84 Latitude |
| `longitude` | Float | WGS84 Longitude |
| `canopy_pct_campus` | Float | Tree canopy percentage on school campus parcel |
| `canopy_pct_250m` | Float | Tree canopy percentage within 250m pedestrian buffer |
| `temp_af` | Float | Afternoon air temperature at school centroid (°F) |
| `anom_af` | Float | Afternoon temperature departure from regional mean (°F) |
| `heat_percentile` | Float | Afternoon heat exposure percentile rank ($0.0 \dots 100.0$) |
| `spot_af` | String | Hot/cold spot status at campus location |

---

## 5. Web Dashboard Binary Data Formats (`web_dashboard/data/`)

To enable client-side sub-5 millisecond canvas repainting of 144,438 grid cells without server dependencies, data is stored in memory-aligned binary arrays:

### `grid_data.bin` Memory Layout
Packed single contiguous array storing 12 consecutive attributes per cell across 144,438 cells ($N = 144,438$):

| Attribute | Data Type | Byte Offset | Scaling / Precision | NoData Value |
| :--- | :--- | :--- | :--- | :--- |
| `inside` | `Uint8` | $0$ | $1 = \text{in study area}, 0 = \text{outside}$ | `0` |
| `canopy` | `Uint8` | $1 \times N$ | Direct percentage ($0 \dots 100$) | `255` |
| `pers` | `Uint8` | $2 \times N$ | Diurnal persistence code ($0 \dots 3$) | `0` |
| `temp_am` | `Int16` (LE) | $3 \times N$ | Temperature in °F $\times 10$ ($0.1^\circ\text{F}$ precision) | `-32768` |
| `temp_af` | `Int16` (LE) | $5 \times N$ | Temperature in °F $\times 10$ | `-32768` |
| `temp_pm` | `Int16` (LE) | $7 \times N$ | Temperature in °F $\times 10$ | `-32768` |
| `anom_am` | `Int16` (LE) | $9 \times N$ | Anomaly in °F $\times 100$ ($0.01^\circ\text{F}$ precision) | `-32768` |
| `anom_af` | `Int16` (LE) | $11 \times N$ | Anomaly in °F $\times 100$ | `-32768` |
| `anom_pm` | `Int16` (LE) | $13 \times N$ | Anomaly in °F $\times 100$ | `-32768` |
| `spot_am` | `Uint8` | $15 \times N$ | Categorical spot code ($1 \dots 7$) | `0` |
| `spot_af` | `Uint8` | $16 \times N$ | Categorical spot code ($1 \dots 7$) | `0` |
| `spot_pm` | `Uint8` | $17 \times N$ | Categorical spot code ($1 \dots 7$) | `0` |
| `z_am` | `Int8` | $18 \times N$ | Standardized z-score rounded to integer | `-128` |
| `z_af` | `Int8` | $19 \times N$ | Standardized z-score rounded to integer | `-128` |
| `z_pm` | `Int8` | $20 \times N$ | Standardized z-score rounded to integer | `-128` |

### `mercator_map.bin` Memory Layout
- Dimensions: $523 \times 479$ pixels ($250,517$ values).
- Data Type: `Int32Array` (Little Endian).
- Value: Linear index into the $362 \times 399$ grid, or `-1` if the pixel falls outside the grid boundary.

