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

def run_script(script_path: Path) -> bool:
    print(f"\n---> Executing: {script_path.relative_to(PROJECT_ROOT)}")
    t0 = time.time()
    res = subprocess.run([sys.executable, str(script_path)])
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

    stages_to_run = list(STAGES.keys()) if args.stage == "all" else [args.stage]

    print("\n" + "=" * 65)
    print("  NORTHERN VIRGINIA URBAN HEAT ISLAND ANALYSIS PIPELINE")
    print("=" * 65)
    print(f"Selected stage(s): {', '.join(stages_to_run)}")

    overall_start = time.time()
    total_scripts = sum(len(STAGES[s]["scripts"]) for s in stages_to_run)
    completed_scripts = 0

    for stage_key in stages_to_run:
        stage = STAGES[stage_key]
        print(f"\n=================================================================")
        print(f"  {stage['title']}")
        print(f"=================================================================")

        for script in stage["scripts"]:
            if not script.exists():
                print(f"Error: Script not found: {script}")
                sys.exit(1)
            success = run_script(script)
            if not success:
                print(f"\nPipeline halted due to error in {script.name}")
                sys.exit(1)
            completed_scripts += 1

    total_time = time.time() - overall_start
    print("\n" + "=" * 65)
    print(f"  PIPELINE EXECUTION COMPLETE")
    print(f"  {completed_scripts}/{total_scripts} scripts executed successfully in {total_time:.1f}s")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()

