"""Local-coordinate search sweep generator, independent of flight controller."""
import math


def sweep(width_m: float, height_m: float, spacing_m: float):
    """Return alternating east/north tracks including both area boundaries.

    This geometric baseline assumes an obstacle-free rectangle. It does not
    model camera footprint, terrain, flight dynamics or geofence compliance.
    """
    values = (width_m, height_m, spacing_m)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Dimensions and spacing must be finite and positive")
    rows = math.ceil(height_m / spacing_m) + 1
    if rows > 100_000:
        raise ValueError("Too many tracks; increase spacing")
    points = []
    for row in range(rows):
        north = height_m * row / (rows - 1)
        ends = (0.0, width_m) if row % 2 == 0 else (width_m, 0.0)
        points.extend((east, north) for east in ends)
    return points
