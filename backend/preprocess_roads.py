"""
Top-level compatibility shim. Real implementation located in scripts/preprocess_roads.py.
"""
import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from scripts.preprocess_roads import *  # noqa: F401, F403
