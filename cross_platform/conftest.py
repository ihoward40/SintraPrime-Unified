"""
conftest.py for SintraPrime cross_platform tests.

This conftest.py is collected when running:
  python -m pytest cross_platform/tests/ -v

It ensures the cross_platform/ directory is on sys.path so that
modules can be imported directly (e.g. from platform_detector import ...).
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add cross_platform directory to sys.path
# This allows: from platform_detector import PlatformDetector
CP_DIR = str(Path(__file__).parent)
if CP_DIR not in sys.path:
    sys.path.insert(0, CP_DIR)
