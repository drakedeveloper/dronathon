"""Generate and detect a local ArUco target; no camera/network needed."""
from pathlib import Path
import cv2
import numpy as np

out = Path(__file__).resolve().parents[1] / "artifacts"
out.mkdir(exist_ok=True)
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
marker = cv2.aruco.generateImageMarker(dictionary, 7, 240)
image = np.full((400, 400), 255, dtype=np.uint8)
image[80:320, 80:320] = marker
corners, ids, _ = cv2.aruco.ArucoDetector(dictionary).detectMarkers(image)
assert ids is not None and 7 in ids.flatten(), "Marker detection failed"
cv2.imwrite(str(out / "marker-7.png"), image)
print("Vision OK: detected marker 7; artifacts/marker-7.png")
