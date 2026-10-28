#!/usr/bin/env python3
"""
Forwarder for scripts/02_temperature/add_temperature_to_grid.py
Maintained for backwards compatibility.
"""
import sys
import subprocess
from pathlib import Path

target = Path(__file__).resolve().parent / "scripts" / "02_temperature" / "add_temperature_to_grid.py"

if __name__ == "__main__":
    result = subprocess.run([sys.executable, str(target)] + sys.argv[1:])
    sys.exit(result.returncode)
