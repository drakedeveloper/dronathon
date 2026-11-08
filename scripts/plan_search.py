"""Export an illustrative coverage plan; does not connect to a drone."""
import argparse
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.coverage import sweep

parser = argparse.ArgumentParser()
parser.add_argument("--width", type=float, default=100)
parser.add_argument("--height", type=float, default=80)
parser.add_argument("--spacing", type=float, default=10)
args = parser.parse_args()
points = sweep(args.width, args.height, args.spacing)
out = root / "artifacts"
out.mkdir(exist_ok=True)
(out / "search-plan.json").write_text(json.dumps({"frame": "local east/north, metres", "points": points}, indent=2))
east, north = zip(*points)
fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(east, north, "o-", linewidth=2)
ax.set(xlabel="East (m)", ylabel="North (m)", title="Search coverage baseline - obstacle-free area")
ax.set_aspect("equal")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out / "search-plan.png", dpi=150)
print(f"Exported {len(points)} waypoints to artifacts/search-plan.json and .png")
