#!/usr/bin/env python3
"""
Forwarder for scripts/03_hotspots/generate_significance_maps.py
Maintained for backwards compatibility.
"""
import sys
import subprocess
from pathlib import Path

target = Path(__file__).resolve().parent / "scripts" / "03_hotspots" / "generate_significance_maps.py"

if __name__ == "__main__":
    result = subprocess.run([sys.executable, str(target)] + sys.argv[1:])
    sys.exit(result.returncode)
