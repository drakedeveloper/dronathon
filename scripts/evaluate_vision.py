import json
import time
from collections import defaultdict
from pathlib import Path
import cv2
from skyforge.scene import CLASSES,ROOT
from skyforge.vision import VisionSystem


def iou(a,b):
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    intersection=max(0,x1-x0)*max(0,y1-y0)
    return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


import argparse
parser=argparse.ArgumentParser();parser.add_argument('--backend',choices=['forest','onnx'],default='forest')
parser.add_argument('--dataset',type=Path,default=ROOT/'data/synthetic')
parser.add_argument('--size',type=int,choices=[384,512],default=512)
parser.add_argument('--primary-size',type=int,choices=[384,512]);args=parser.parse_args()
folder=args.dataset;manifest=json.loads((folder/"manifest.json").read_text())
if args.backend=='onnx':
    from skyforge.neural_vision import NeuralVisionSystem
    model=NeuralVisionSystem(ROOT/'models',size=args.size,primary_size=args.primary_size)
else:model=VisionSystem(ROOT/"models")
counts=defaultdict(lambda:{"tp":0,"fp":0,"fn":0});durations=[]
for i,item in enumerate(manifest):
    if item["split"]!="val":continue
    image=cv2.imread(str(folder/item["image"]));start=time.perf_counter_ns()
    result=model.infer(image,{"frame_id":i,"t_sim_ns":0});durations.append((time.perf_counter_ns()-start)/1e6)
    used=set()
    for pred in sorted(result["detections"],key=lambda d:-d["confidence"]):
        options=[(iou(pred["bbox_xyxy"],gt["bbox_xyxy"]),j) for j,gt in enumerate(item["boxes"]) if CLASSES[gt["label"]]==pred["class"] and j not in used]
        overlap,j=max(options,default=(0,-1))
        if overlap>=.5:counts[pred["class"]]["tp"]+=1;used.add(j)
        else:counts[pred["class"]]["fp"]+=1
    for j,gt in enumerate(item["boxes"]):
        if j not in used:counts[CLASSES[gt["label"]]]["fn"]+=1
for name,c in counts.items():
    c["precision"]=c["tp"]/max(1,c["tp"]+c["fp"]);c["recall"]=c["tp"]/max(1,c["tp"]+c["fn"])
import numpy as np
report={"domain":"rendered validation scenes, used for development tuning; fresh final test still required","iou_threshold":.5,"counts":dict(counts),"inference_p95_ms":float(np.percentile(durations,95)),"images":len(durations)}
report['backend']=args.backend
report['input_size']=args.size if args.backend=='onnx' else None
report['primary_size']=args.primary_size or args.size
suffix=f'-primary{args.primary_size}' if args.primary_size else ''
(ROOT/f"artifacts/vision-evaluation-{args.backend}-{args.size}{suffix}.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
