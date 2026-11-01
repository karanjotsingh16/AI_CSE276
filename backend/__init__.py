"""
NER SmartRoute — Backend Package
Ensures core algorithms, domain services, scripts, and tests are directly accessible.
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
for _subdir in ["core", "services", "scripts", "tests"]:
    _subpath = str(_BACKEND_DIR / _subdir)
    if _subpath not in sys.path:
        sys.path.insert(0, _subpath)

