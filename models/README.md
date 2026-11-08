# Model artifacts

`primary.pt` / `primary.onnx`: YOLO11n, waste/mine/weapon.
`secondary.pt` / `secondary.onnx`: YOLO11n, injured_person/hostile_unit.
Static ONNX input1x3x512x512, opset17, CPU execution. Both trained30epochs on70
synthetic Gazebo images,20development-validation images. Role cues and simple
props are declared scenario conventions, not real-world clinical recognition.

`*-metrics.json` contains Ultralytics development metrics. High mAP50 from this
tiny scene-specific set is not evidence of generalisation. At confidence0.35 and
IoU0.5 the512custom inference adapter detected9/9casualties,6/6mines,6/6waste,
1/1hostile and1/2weapon instances on20development images. A new final test is
still required. Dataset seed33 was already inspected and is not a blind test.

`*-384.onnx` are smaller-input experimental exports from identical weights.
Development casualty TP drops to7/9 with2false positives at IoU0.5; not default.
Native Windows timing~41ms p95 for both384models; timing is machine/load-specific
and excludes image capture, transport, planning and actuation.

`pixel_forest.xml` and `region_svm.xml` provide the earlier rendered pixel/HOG
baseline; `model-card.json` describes it. Use `SKYFORGE_VISION=forest` to compare.
Ultralytics upstream software/model terms apply; see THIRD_PARTY_NOTICES.md.
