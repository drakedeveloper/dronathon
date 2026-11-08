"""Validate the proposed inter-team fixtures; no ROS/simulator needed."""
import json
import math
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1] / "contracts"


def reject_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON number")
    if isinstance(value, dict):
        for item in value.values():
            reject_nonfinite(item)
    if isinstance(value, list):
        for item in value:
            reject_nonfinite(item)


def validate(name, payload):
    schema = json.loads((ROOT / f"{name}-v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    reject_nonfinite(payload)
    if name == "detections":
        width, height = payload["image_size_wh"]
        for detection in payload["detections"]:
            x0, y0, x1, y1 = detection["bbox_xyxy"]
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                raise ValueError("Box is outside the original image or has zero/negative area")
            expected = "secondary" if detection["class"] in ("injured_person", "hostile_unit") else "primary"
            if detection["source"] not in (expected, "mock"):
                raise ValueError("Class and detector source disagree")


if __name__ == "__main__":
    for name in ("detections", "decision"):
        validate(name, json.loads((ROOT / "examples" / f"{name}.json").read_text()))
        print(f"{name}: schema and geometry OK")
