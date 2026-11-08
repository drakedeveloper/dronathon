# Dataset/model handoff

Latest user decision: teammate handles the three supplied real-image datasets.
Do not duplicate that training while the simulator release is being stabilized.

Downloaded locally (ignored by Git):

- data/external/gun-detection.zip — supplied Kaggle Gunmen dataset, 1,310 images.
  The archive's classes.txt includes unused names; labels actually use index15
  `Human` and index16 `Gun`. Map Gun to primary `weapon`. Do not label every human
  as hostile or injured; these images do not provide injury/hostility labels.
- data/external/coastal-litter.rar — original Zenodo Data.rar. It contains YOLO
  polygon segmentation labels, seven material classes. Convert polygons to
  bounding boxes explicitly and map them to `waste` for our primary interface.
  Keep source labels/provenance; do not treat polygon rows as xywh boxes.
- Mine dataset was verified public-domain with one `mine` class and 501 images.
  No account/export credentials are stored. Teammate owns export/training.

Do not mix augmented derivatives or duplicate originals across splits. Preserve
the 70/20/10 requirement in the final agreed data manifest and report per-class
recall/AP for real data separately from simulator images. Current native-scene
metrics are development results and are not evidence of photographic accuracy.

## Drop-in exported models

The primary ONNX model must take float32 RGB NCHW [1,3,512,512], normalized 0..1
with letterboxing. Output must match YOLO11 detection [1,7,5376] for three
classes ordered `waste`, `mine`, `weapon` (4 box values + 3 scores).
The secondary has two classes `injured_person`, `hostile_unit`, output
[1,6,5376]. Alternative outputs require an explicit adapter, not silent relabeling.

Provide ONNX, source weights, class map, preprocessing description, dataset
manifest/splits, validation metrics and model SHA256. Save candidate models in a
new folder. Existing models/ is the Gazebo baseline; artifacts/native_v3_models
is the current native candidate. Never overwrite both without comparison.

Check a candidate locally:

```powershell
& "$env:LOCALAPPDATA\SKYFORGE\venv-native\Scripts\python.exe" -m scripts.evaluate_vision --backend onnx --device cuda --dataset PATH_TO_MANIFEST_DATASET --models PATH_TO_CANDIDATE
```

The manifest schema is illustrated by data/native-v3/manifest.json: image path,
split, image_size_wh, and boxes with label1..5 and bbox_xyxy. Use val for tuning;
freeze model/thresholds before a final held-out test. A good real-data score does
not replace a camera-driven simulated mission and independent delivery audit.
