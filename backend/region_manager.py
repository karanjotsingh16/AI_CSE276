"""
Top-level compatibility shim. Real implementation located in core/region_manager.py.
"""
import sys
from pathlib import Path

_CORE = str(Path(__file__).resolve().parent / "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from core.region_manager import *  # noqa: F401, F403
from core.region_manager import RegionGraphManager
