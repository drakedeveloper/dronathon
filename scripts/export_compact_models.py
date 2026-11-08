"""Export smaller input variants without replacing the verified512 models."""
from pathlib import Path
import shutil
import torch
from ultralytics import YOLO

torch.set_num_threads(2)
root=Path(__file__).resolve().parents[1]
for kind in ('primary','secondary'):
    temporary=root/'artifacts/compact-export';temporary.mkdir(parents=True,exist_ok=True)
    weights=temporary/f'{kind}.pt';shutil.copy2(root/'models'/f'{kind}.pt',weights)
    model=YOLO(str(weights))
    exported=model.export(format='onnx',imgsz=384,batch=1,dynamic=False,simplify=True,opset=17)
    shutil.copy2(exported,root/'models'/f'{kind}-384.onnx')
    print('Exported',kind,384,flush=True)
