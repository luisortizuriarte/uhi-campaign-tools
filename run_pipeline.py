#!/usr/bin/env python3
"""
run_pipeline.py - Master CLI Runner for the NOVA Urban Heat Island Analysis Pipeline.

Executes scientific stages end-to-end or individually:
  Stage 1 (canopy)      : High-performance tree canopy rasterization & aggregation
  Stage 2 (temperature) : Zonal temperature mean and anomaly calculations
  Stage 3 (hotspots)    : Spatial autocorrelation (Getis-Ord Gi*) & persistence modeling
  Stage 4 (schools)     : School heat vulnerability & canopy buffer analysis
  Stage 5 (graphics)    : 16:9 presentation figures & transparent slide maps
  Stage 6 (export)      : Compact binary & GeoJSON export for web dashboard
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

STAGES = {
    "canopy": {
        "title": "Stage 1: Tree Canopy Ingestion & Aggregation",
        "scripts": [
            PROJECT_ROOT / "scripts" / "01_canopy" / "make_canopy_grid.py",
            PROJECT_ROOT / "scripts" / "01_canopy" / "validate_canopy.py",
            PROJECT_ROOT / "scripts" / "01_canopy" / "make_canopy_map.py",
        ],
    },
    "temperature": {
        "title": "Stage 2: Zonal Temperature & Anomaly Processing",
        "scripts": [
            PROJECT_ROOT / "scripts" / "02_temperature" / "add_temperature_to_grid.py",
            PROJECT_ROOT / "scripts" / "02_temperature" / "make_uhi_maps.py",
            PROJECT_ROOT / "scripts" / "02_temperature" / "generate_measurement_maps.py",
        ],
    },
    "hotspots": {
        "title": "Stage 3: Spatial Hotspot & Anomaly Clustering",
        "scripts": [
            PROJECT_ROOT / "scripts" / "03_hotspots" / "make_hotspot_analysis.py",
            PROJECT_ROOT / "scripts" / "03_hotspots" / "generate_significance_maps.py",
        ],
    },
    "schools": {
        "title": "Stage 4: School Heat Exposure & Vulnerability",
        "scripts": [
            PROJECT_ROOT / "scripts" / "04_schools_exposure" / "process_schools.py",
            PROJECT_ROOT / "scripts" / "04_schools_exposure" / "analyze_schools.py",
        ],
    },
    "graphics": {
        "title": "Stage 5: Presentation Graphics & Slide Cartography",
        "scripts": [
            PROJECT_ROOT / "scripts" / "05_presentation_graphics" / "export_transparent_maps.py",
            PROJECT_ROOT / "scripts" / "05_presentation_graphics" / "create_quintile_options.py",
            PROJECT_ROOT / "scripts" / "05_presentation_graphics" / "make_analysis_plots.py",
        ],
    },
    "export": {
        "title": "Stage 6: Web Dashboard Data Product Export",
        "scripts": [
            PROJECT_ROOT / "scripts" / "06_dashboard_export" / "build_dashboard_data.py",
        ],
    },
}

VARIABLE_SUPPORTED_STAGES = {"temperature", "hotspots", "schools", "graphics"}


def run_script(script_path: Path, extra_args: list[str] | None = None) -> bool:
    cmd = [sys.executable, str(script_path)] + (extra_args or [])
    arg_str = f" {' '.join(extra_args)}" if extra_args else ""
    print(f"\n---> Executing: {script_path.relative_to(PROJECT_ROOT)}{arg_str}")
    t0 = time.time()
    res = subprocess.run(cmd)
    elapsed = time.time() - t0
    if res.returncode == 0:
        print(f"     [SUCCESS] Completed in {elapsed:.1f}s")
        return True
    else:
        print(f"     [FAILED] Exited with code {res.returncode} after {elapsed:.1f}s")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Master CLI Runner for the NOVA Urban Heat Island Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stage",
        choices=["all", "canopy", "temperature", "hotspots", "schools", "graphics", "export"],
        default="all",
        help="Pipeline stage to execute (default: all)",
    )
    parser.add_argument(
        "--variable",
        choices=["temperature", "heat_index", "both"],
        default="temperature",
        help="Climatic variable to analyze: 'temperature', 'heat_index', or 'both' (default: temperature)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pipeline stages and their scripts without executing",
    )
    args = parser.parse_args()

    if args.list:
        print("\n================ NOVA UHI Pipeline Stages ================")
        for key, stage_info in STAGES.items():
            print(f"\n[{key.upper()}] - {stage_info['title']}")
            for s in stage_info["scripts"]:
                print(f"  • {s.relative_to(PROJECT_ROOT)}")
        print("\n==========================================================")
        return

    variables_to_run = ["temperature", "heat_index"] if args.variable == "both" else [args.variable]
    shared_canopy_exists = (
        Path("output/canopy/grid-canopy.gpkg").is_file()
        and Path("output/canopy/canopy_mask_1m.tif").is_file()
    )
    shared_schools_exist = Path("output/locations/school_locs.gpkg").is_file()

    if args.stage == "all":
        stages_to_run = ["temperature", "hotspots", "schools", "graphics"]
        if not shared_canopy_exists:
            stages_to_run.insert(0, "canopy")
    else:
        stages_to_run = [args.stage]

    print("\n" + "=" * 65)
    print("  NORTHERN VIRGINIA URBAN HEAT ISLAND ANALYSIS PIPELINE")
    print("=" * 65)
    print(f"Selected variable(s): {', '.join(variables_to_run)}")
    print(f"Selected stage(s):    {', '.join(stages_to_run)}")

    overall_start = time.time()
    completed_scripts = 0
    total_scripts = 0

    for var_key in variables_to_run:
        print("\n" + "#" * 65)
        print(f"  RUNNING PIPELINE FOR VARIABLE: {var_key.upper()}")
        print("#" * 65)

        for stage_key in stages_to_run:
            if var_key == "heat_index" and stage_key in ("canopy", "export"):
                print(f"\n[SKIP] Stage '{stage_key}' is shared/excluded for '{var_key}'.")
                continue

            stage = STAGES[stage_key]
            print(f"\n=================================================================")
            print(f"  {stage['title']} [{var_key}]")
            print(f"=================================================================")

            scripts = list(stage["scripts"])
            if stage_key == "schools" and shared_schools_exist:
                # Preserve existing school_locs.gpkg and only write variable-specific buffers & figures
                scripts = [s for s in scripts if s.name != "process_schools.py"]

            extra = ["--variable", var_key] if stage_key in VARIABLE_SUPPORTED_STAGES else []
            total_scripts += len(scripts)

            for script in scripts:
                if not script.exists():
                    print(f"Error: Script not found: {script}")
                    sys.exit(1)
                success = run_script(script, extra_args=extra)
                if not success:
                    print(f"\nPipeline halted due to error in {script.name} ({var_key})")
                    sys.exit(1)
                completed_scripts += 1

    total_time = time.time() - overall_start
    print("\n" + "=" * 65)
    print(f"  PIPELINE EXECUTION COMPLETE")
    print(f"  {completed_scripts}/{total_scripts} scripts executed successfully in {total_time:.1f}s")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()

