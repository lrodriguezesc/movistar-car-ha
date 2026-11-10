"""Load the integration modules without importing Home Assistant.

The package __init__ imports Home Assistant. These tests only need the pure
modules (api, const, consumption, helpers), so we register an empty package
that points to the folder and skip __init__.
"""

import sys
import types
from pathlib import Path

PKG_DIR = Path(__file__).parent.parent / "custom_components" / "movistar_car"

pkg = types.ModuleType("movistar_car")
pkg.__path__ = [str(PKG_DIR)]
sys.modules.setdefault("movistar_car", pkg)
