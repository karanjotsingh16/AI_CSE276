"""
Top-level compatibility shim. Real implementation located in services/accessibility_service.py.
"""
import sys
from pathlib import Path

_SVC = str(Path(__file__).resolve().parent / "services")
if _SVC not in sys.path:
    sys.path.insert(0, _SVC)

from services.accessibility_service import *  # noqa: F401, F403
from services.accessibility_service import AccessibilityService, UPLOADS_DIR
