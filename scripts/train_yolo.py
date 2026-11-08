"""Train separate primary/secondary networks on the current rendered dataset.

Real linked-dataset adaptation is a separate required evaluation task; this
script never claims synthetic metrics demonstrate photographic performance.
"""
import argparse
import json
import os
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def prepare(kind):
    source=ROOT/"data/synthetic";target=ROOT/"data"/f"yolo_{kind}"
    mapping={1:0,2:1,3:2} if kind=="primary" else {4:0,5:1}
    names=["waste","mine","weapon"] if kind=="primary" else ["injured_person","hostile_unit"]
    for item in json.loads((source/"manifest.json").read_text()):
        split=item["split"];images=target/"images"/split;labels=target/"labels"/split
        images.mkdir(parents=True,exist_ok=True);labels.mkdir(parents=True,exist_ok=True)
        image=source/item["image"];destination=images/image.name
        if not destination.exists():
            try:os.link(image,destination)
            except OSError:shutil.copy2(image,destination)
        rows=[]
        for box in item["boxes"]:
            if box["label"] not in mapping:continue
            x0,y0,x1,y1=box["bbox_xyxy"]
            x0=max(0,min(640,x0));x1=max(0,min(640,x1));y0=max(0,min(480,y0));y1=max(0,min(480,y1))
            if x1<=x0 or y1<=y0:continue
            rows.append(f'{mapping[box["label"]]} {(x0+x1)/1280:.7f} {(y0+y1)/960:.7f} {(x1-x0)/640:.7f} {(y1-y0)/480:.7f}')
        (labels/(image.stem+".txt")).write_text("\n".join(rows))
    import yaml
    config=target/"data.yaml"
    config.write_text(yaml.safe_dump({"path":str(target),"train":"images/train","val":"images/val","test":"images/test","names":names}))
    return config


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--kind",choices=["primary","secondary","both"],default="both")
    parser.add_argument("--epochs",type=int,default=35);parser.add_argument("--device",default="cpu");args=parser.parse_args()
    import torch
    torch.set_num_threads(4)
    from ultralytics import YOLO
    for kind in (["primary","secondary"] if args.kind=="both" else [args.kind]):
        config=prepare(kind)
        model=YOLO("yolo11n.pt")
        model.train(data=str(config),epochs=args.epochs,imgsz=512,batch=8,device=args.device,workers=0,
                    project=str(ROOT/"artifacts/yolo_runs"),name=kind,exist_ok=True,cache=False,plots=False,
                    patience=12,seed=2026,deterministic=True,degrees=180,flipud=.5,fliplr=.5,
                    hsv_h=.015,hsv_s=.45,hsv_v=.35,close_mosaic=5,verbose=True)
        weights=ROOT/"artifacts/yolo_runs"/kind/"weights/best.pt"
        trained=YOLO(str(weights))
        metrics=trained.val(data=str(config),split="val",plots=False,device=args.device)
        output=ROOT/"models";output.mkdir(exist_ok=True)
        shutil.copy2(weights,output/f"{kind}.pt")
        exported=trained.export(format="onnx",imgsz=512,batch=1,dynamic=False,simplify=True,opset=17)
        shutil.copy2(exported,output/f"{kind}.onnx")
        (output/f"{kind}-metrics.json").write_text(json.dumps({"domain":"rendered development validation",**metrics.results_dict},indent=2))
