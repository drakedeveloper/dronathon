"""Offline smoke checks for the hackathon workstation."""
import importlib
import json
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result = {"python": sys.version, "executable": sys.executable}
for name in ("numpy", "scipy", "matplotlib", "cv2", "pymavlink", "mavsdk", "serial", "yaml", "rich", "pytest"):
    module = importlib.import_module(name)
    result[name] = getattr(module, "__version__", "import OK")
import cv2
assert hasattr(cv2, "aruco"), "ArUco module is required"
result["D_free_GiB"] = round(shutil.disk_usage(root).free / 2**30, 2)
print(json.dumps(result, indent=2))
(root / "artifacts").mkdir(exist_ok=True)
(root / "artifacts" / "environment.json").write_text(json.dumps(result, indent=2))
