import math
import pytest
from src.coverage import sweep


@pytest.mark.parametrize("height,spacing", [(80, 10), (83, 10), (5, 20)])
def test_covers_boundaries_without_exceeding_track_spacing(height, spacing):
    points = sweep(100, height, spacing)
    tracks = points[::2]
    assert tracks[0][1] == 0 and tracks[-1][1] == height
    assert all(0 < b[1] - a[1] <= spacing for a, b in zip(tracks, tracks[1:]))
    assert all(0 <= x <= 100 and 0 <= y <= height for x, y in points)
    assert all(a[0] == b[0] for a, b in zip(points[1::2], points[2::2]))


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan])
def test_rejects_invalid_dimensions(value):
    with pytest.raises(ValueError):
        sweep(100, value, 10)
