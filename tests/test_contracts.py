"""Meaningful cross-team interface checks for malformed model output."""
import copy
import json
from pathlib import Path
import pytest
from scripts.validate_contracts import validate

ROOT = Path(__file__).resolve().parents[1] / "contracts" / "examples"


def fixture(name):
    return json.loads((ROOT / f"{name}.json").read_text())


def test_shared_examples_are_valid():
    validate("detections", fixture("detections"))
    validate("decision", fixture("decision"))


@pytest.mark.parametrize("box", [[10, 10, 9, 20], [0, 0, 641, 20], [0, 0, 20, 481], [0, 0, 0, 1]])
def test_rejects_model_box_coordinate_errors(box):
    batch = fixture("detections")
    batch["detections"][0]["bbox_xyxy"] = box
    with pytest.raises(ValueError):
        validate("detections", batch)


def test_rejects_class_source_mixup():
    batch = fixture("detections")
    batch["detections"][0]["source"] = "primary"
    with pytest.raises(ValueError):
        validate("detections", batch)


def test_rejects_nonfinite_waypoint():
    proposal = copy.deepcopy(fixture("decision"))
    proposal["waypoints_enu_m"][0][0] = float("nan")
    with pytest.raises(ValueError):
        validate("decision", proposal)
