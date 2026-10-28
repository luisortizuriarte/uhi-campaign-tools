# Northern Virginia (NOVA) Urban Heat Island Analysis Tools

Scientific data processing and spatial analysis toolkit for the Northern Virginia Urban Heat Island (UHI) Mapping Campaign. This toolkit processes high-resolution mobile traverse observations, continuous modeled temperature surfaces, and jurisdictional tree canopy polygons across Fairfax County, Arlington County, and the City of Alexandria.

---

## Environment Requirements

- **Python**: `>= 3.11`
- **Key Dependencies**:
  - Spatial & Raster Processing: `geopandas`, `rasterio`, `xarray`, `rioxarray`, `pyproj`, `shapely`, `pyogrio`
  - Scientific Computing & Statistics: `numpy`, `scipy`, `pandas`, `libpysal`, `esda`
  - Visualization: `matplotlib`, `contextily`

### Setup Instructions

1. **Create and Activate Environment** (via Conda/Mamba using `environment.yml`):
   ```bash
   conda env create -f environment.yml
   conda activate uhidata
   ```

2. **Install the `uhi` Library in Editable Mode**:
   ```bash
   pip install -e .
   ```

3. **Verify Installation** (run automated test suite):
   ```bash
   python -m unittest discover tests
   ```

---

## Analysis Tools Overview

The analysis toolkit is structured into a modular Python package (`uhi/`) and numbered execution stages (`scripts/`):

### 1. Core Scientific Library (`uhi/`)
- **`uhi.canopy`**: High-performance rasterization of millions of vector tree canopy polygons and block aggregation into 100m grid cells.
- **`uhi.zonal`**: Extraction of zonal mean temperatures and domain spatial anomalies for Morning (AM: 6–7 AM), Afternoon (AF: 3–4 PM), and Evening (PM: 7–8 PM) observation periods.
- **`uhi.hotspots`**: Spatial autocorrelation modeling using Getis-Ord $G_i^*$, local z-score clustering (90%, 95%, 99% confidence levels), and diurnal persistence classification (persistent hot, persistent cold, variable).
- **`uhi.school_analysis`**: Vulnerability modeling computing radial tree canopy buffers and temperature anomaly percentiles for educational facilities and community locations.
- **`uhi.plotting` & `uhi.canopy_plots`**: Cartographic and charting engines for generating publication-quality 16:9 presentation graphics and transparent slide overlays.
- **`uhi.io`**: Input/output loaders with CRS verification and spatial boundary clipping for GeoPackages, shapefiles, and GeoTIFFs.

### 2. Pipeline Execution Stages (`scripts/`)
- **`scripts/01_canopy/`**:
  - `make_canopy_grid.py`: Ingests jurisdictional tree canopy polygons and aggregates coverage percentages to the study grid.
  - `validate_canopy.py`: Validates raster aggregation against vector geometries.
  - `make_canopy_map.py`: Produces overview canopy maps.
- **`scripts/02_temperature/`**:
  - `add_temperature_to_grid.py`: Samples continuous temperature GeoTIFFs onto analytical grid cells.
  - `make_uhi_maps.py`: Generates diurnal temperature and anomaly cartography.
  - `generate_measurement_maps.py`: Plots raw mobile sensor traverse tracks.
- **`scripts/03_hotspots/`**:
  - `make_hotspot_analysis.py`: Computes spatial autocorrelation and Getis-Ord $G_i^*$ statistics.
  - `generate_significance_maps.py`: Renders statistically significant hot and cold spot cluster maps.
- **`scripts/04_schools_exposure/`**:
  - `process_schools.py`: Consolidates and standardizes school point and building footprint locations.
  - `analyze_schools.py`: Calculates surrounding tree canopy buffers and heat vulnerability rankings.
- **`scripts/05_presentation_graphics/`**:
  - `export_transparent_maps.py`: Renders borderless, high-resolution transparent PNG maps.
  - `create_quintile_options.py`: Computes canopy quintile temperature distributions.
  - `make_analysis_plots.py`: Generates comparative bar charts and diurnal variation graphics.
- **`scripts/06_dashboard_export/`**:
  - `build_dashboard_data.py`: Packs grid attributes and mercator bounds into compact binary formats for web exploration.

---

## How to Run

### Using the Master Pipeline CLI (`run_pipeline.py`)

The pipeline runner orchestrates stages individually or end-to-end:

```bash
# List all available stages and their scripts
python run_pipeline.py --list

# Run a specific stage:
python run_pipeline.py --stage canopy       # Stage 1: Tree canopy aggregation
python run_pipeline.py --stage temperature  # Stage 2: Zonal temperatures & UHI maps
python run_pipeline.py --stage hotspots     # Stage 3: Spatial clustering & persistence
python run_pipeline.py --stage schools      # Stage 4: School heat exposure & buffers
python run_pipeline.py --stage graphics     # Stage 5: Presentation graphics & transparent maps
python run_pipeline.py --stage export       # Stage 6: Binary data export

# Run the complete pipeline end-to-end:
python run_pipeline.py --stage all
```

### Running Individual Stage Scripts Directly

Each script can be executed standalone from the project root:

```bash
# Example: Aggregating canopy percentage onto grid
python scripts/01_canopy/make_canopy_grid.py

# Example: Hotspot and spatial persistence analysis
python scripts/03_hotspots/make_hotspot_analysis.py

# Example: School heat exposure analysis
python scripts/04_schools_exposure/analyze_schools.py
```
