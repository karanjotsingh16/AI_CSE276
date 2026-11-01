"""
NER SmartRoute — Test Suite Package
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _subdir in [_BACKEND_DIR, _BACKEND_DIR / "core", _BACKEND_DIR / "services", _BACKEND_DIR / "scripts"]:
    _subpath = str(_subdir)
    if _subpath not in sys.path:
        sys.path.insert(0, _subpath)

