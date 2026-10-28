# Northern Virginia (NOVA) Urban Heat Island Scientific Analysis Pipeline

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Conda Environment](https://img.shields.io/badge/Environment-Conda%20Forge-green.svg)](environment.yml)
[![Pytest Test Suite](https://img.shields.io/badge/Tests-Pytest-orange.svg)](tests/)

This repository contains the scientific data processing pipeline for the **Northern Virginia (NOVA) Urban Heat Island (UHI) Mapping Campaign**. It processes field measurements, jurisdictional tree canopy polygons, and machine-learning continuous temperature surfaces across **Fairfax County**, **Arlington County**, and the **City of Alexandria**.

For technical architecture and data flow, see [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md).  
For complete attribute definitions and CRS specifications, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md).  
For the interactive public explorer, see the sister repository in [`web_dashboard/`](web_dashboard/README.md).

---

## Key Capabilities

1. **Streaming C++ Tree Canopy Aggregation**: Scalable rasterization (`gdal_rasterize`) of 3.5+ million jurisdictional tree canopy polygons into a unified 1m mask, followed by block-strided window aggregation across 144,438 nominal 100m grid cells. Mean absolute error vs. exact Shapely intersection: **0.05 percentage points**.
2. **Diurnal Microclimate Zonal Statistics**: Computes mean temperatures and domain spatial anomalies for Morning (AM: 6–7 AM), Afternoon (AF: 3–4 PM), and Evening (PM: 7–8 PM) mobile survey observation periods.
3. **Spatial Clustering & Hotspot Persistence**: Computes Getis-Ord $G_i^*$ local statistics, z-score clustering at 90%, 95%, and 99% confidence intervals, and classifies diurnal persistence (persistent hot, persistent cold, variable).
4. **Community Vulnerability Modeling**: Computes tree canopy buffers and heat exposure percentile ranks for public schools and public facilities.
5. **16:9 Presentation Cartography**: Generates publication-ready 300 DPI graphics ($4000 \times 2250$ px) adhering to Tufte de-cluttering standards and the Figtree visual guidelines in `GEMINI.md`.
6. **Web Dashboard Serialization**: Extracts and packs the 144,438 analytical cells into sub-5 millisecond binary typed arrays for the standalone client-side web application.

---

## Directory Organization

```
uhi-campaign-tools /
├── run_pipeline.py                 # Master CLI runner to execute all or individual stages
├── pyproject.toml                  # Python package configuration (pip install -e .)
├── environment.yml                 # Conda environment definition (conda-forge)
├── README.md                       # Project documentation (this file)
├── PIPELINE_ARCHITECTURE.md        # Technical pipeline architecture & dataflow
├── DATA_DICTIONARY.md              # Input/output schemas, CRS, and attribute definitions
├── GEMINI.md                       # 16:9 presentation figure styling standards
│
├── uhi/                            # Core Scientific Python Library
│   ├── __init__.py                 # Library exports
│   ├── canopy.py                   # GDAL rasterization & block aggregation
│   ├── zonal.py                    # Zonal statistics & spatial anomalies
│   ├── hotspots.py                 # Spatial autocorrelation (Getis-Ord Gi*, z-scores)
│   ├── school_analysis.py          # School heat exposure & canopy buffers
│   ├── plotting.py                 # 16:9 presentation maps & styling
│   ├── canopy_plots.py             # Canopy quintile comparison graphics
│   ├── hotspot_plots.py            # Significance & cluster plotting utilities
│   ├── locations.py                # Coordinate transforms & feature processing
│   ├── io.py                       # GeoPackage & raster I/O
│   └── style_template.py           # Presentation figure standards & color palettes
│
├── scripts/                        # Numbered Pipeline Execution Stages
│   ├── 01_canopy/                  # Tree canopy rasterization & validation
│   │   ├── make_canopy_grid.py
│   │   ├── validate_canopy.py
│   │   └── make_canopy_map.py
│   ├── 02_temperature/             # Zonal temperature & anomaly mapping
│   │   ├── add_temperature_to_grid.py
│   │   ├── make_uhi_maps.py
│   │   └── generate_measurement_maps.py
│   ├── 03_hotspots/                # Spatial autocorrelation & persistence
│   │   ├── make_hotspot_analysis.py
│   │   └── generate_significance_maps.py
│   ├── 04_schools_exposure/        # Facility exposure & vulnerability
│   │   ├── process_schools.py
│   │   └── analyze_schools.py
│   ├── 05_presentation_graphics/   # Slide cartography & quintile options
│   │   ├── export_transparent_maps.py
│   │   ├── create_quintile_options.py
│   │   └── make_analysis_plots.py
│   └── 06_dashboard_export/        # Web dashboard binary export
│       └── build_dashboard_data.py
│
├── tests/                          # Automated Pytest Suite
│   ├── test_analysis.py
│   ├── test_canopy.py
│   ├── test_canopy_plots.py
│   ├── test_hotspots.py
│   ├── test_locations.py
│   ├── test_school_analysis.py
│   ├── test_style_template.py
│   ├── test_uhi.py
│   └── test_zonal.py
│
├── input_data/                     # Raw Input Datasets (Read-Only)
│   ├── auxilliary/                 # 100m nominal study grid
│   ├── county_boundaries/          # Jurisdictional boundary shapefiles
│   ├── locations/                  # School & landmark coordinates
│   ├── maps/                       # Continuous temperature surface GeoTIFFs
│   ├── tree canopy/                # Jurisdictional canopy shapefiles
│   └── uhi-combined/               # Mobile traverse GPS sensor readings
│
├── output/                         # Generated Pipeline Data Products
│   ├── canopy/                     # grid-canopy.gpkg (144,438 grid features)
│   ├── hotspots/                   # hotspots.gpkg (Master analytical grid)
│   ├── locations/                  # school_heat_exposure.csv
│   └── figures/                    # 300 DPI 16:9 presentation figures
│
└── web_dashboard/                  # Independent Web Dashboard Repository
    └── (See web_dashboard/README.md for standalone web app documentation)
```

---

## Installation & Environment Setup

### 1. Create Conda Environment
Using the provided `environment.yml`:
```bash
conda env create -f environment.yml
conda activate uhidata
```

### 2. Install Core Package in Editable Mode
```bash
pip install -e .
```

### 3. Run Test Suite
```bash
pytest tests/
```

---

## Running the Pipeline

You can run the entire pipeline end-to-end, or execute individual stages using the master CLI runner:

```bash
# List all pipeline stages and their scripts
python run_pipeline.py --list

# Run specific stages:
python run_pipeline.py --stage canopy       # Stage 1: Canopy rasterization & validation
python run_pipeline.py --stage temperature  # Stage 2: Zonal temperatures & UHI maps
python run_pipeline.py --stage hotspots     # Stage 3: Spatial clustering & persistence
python run_pipeline.py --stage schools      # Stage 4: School exposure & vulnerability
python run_pipeline.py --stage graphics     # Stage 5: Presentation figures & slide maps
python run_pipeline.py --stage export       # Stage 6: Web dashboard data packaging

# Run the complete pipeline end-to-end:
python run_pipeline.py --stage all
```

Individual scripts in `scripts/` can also be run directly:
```bash
python scripts/01_canopy/make_canopy_grid.py
python scripts/03_hotspots/make_hotspot_analysis.py
python scripts/06_dashboard_export/build_dashboard_data.py
```
*(Root-level backwards-compatibility wrappers are also maintained for convenience).*

---

## Two-Repository Architecture

This project is partitioned into two distinct, decoupled repositories:

1. **`nova-uhi-analysis` (This Repository)**: Contains the scientific Python codebase, heavy GIS dependencies (GDAL, GeoPandas, rasterio), spatial modeling algorithms, raw datasets, and analytical products.
2. **`nova-uhi-dashboard` ([`web_dashboard/`](web_dashboard/README.md))**: Contains the zero-build, client-side web application. It consumes pre-rendered binary data packages emitted by Stage 6 (`scripts/06_dashboard_export/build_dashboard_data.py`) and can be deployed directly to GitHub Pages or embedded into external websites with zero server dependencies.
