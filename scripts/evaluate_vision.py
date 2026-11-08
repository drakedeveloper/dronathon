import json
import time
from collections import defaultdict
from pathlib import Path
import cv2
from skyforge.scene import CLASSES,ROOT


def iou(a,b):
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    intersection=max(0,x1-x0)*max(0,y1-y0)
    return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


import argparse
parser=argparse.ArgumentParser();parser.add_argument('--backend',choices=['forest','onnx'],default='forest')
parser.add_argument('--dataset',type=Path,default=ROOT/'data/synthetic')
parser.add_argument('--size',type=int,choices=[384,512],default=512)
parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
parser.add_argument('--models',type=Path,default=ROOT/'models')
parser.add_argument('--split',choices=['val','test'],default='val')
parser.add_argument('--kind',choices=['both','primary','secondary'],default='both')
parser.add_argument('--confidence',type=float,default=.35)
parser.add_argument('--primary-size',type=int,choices=[384,512]);args=parser.parse_args()
folder=args.dataset;manifest=json.loads((folder/"manifest.json").read_text())
if args.backend=='onnx':
    from skyforge.neural_vision import NeuralVisionSystem
    kinds=('primary','secondary') if args.kind=='both' else (args.kind,)
    model=NeuralVisionSystem(args.models,size=args.size,primary_size=args.primary_size,device=args.device,kinds=kinds,confidence=args.confidence)
else:
    from skyforge.vision import VisionSystem
    model=VisionSystem(ROOT/"models")
counts=defaultdict(lambda:{"tp":0,"fp":0,"fn":0});durations=[];errors=[]
for i,item in enumerate(manifest):
    if item["split"]!=args.split:continue
    labels=(1,2,3) if args.kind=='primary' else (4,5) if args.kind=='secondary' else (1,2,3,4,5)
    item={**item,'boxes':[box for box in item['boxes'] if box['label'] in labels]}
    image=cv2.imread(str(folder/item["image"]));start=time.perf_counter_ns()
    result=model.infer(image,{"frame_id":i,"t_sim_ns":0});durations.append((time.perf_counter_ns()-start)/1e6)
    allowed={CLASSES[label] for label in labels}
    result['detections']=[d for d in result['detections'] if d['class'] in allowed]
    used=set()
    for pred in sorted(result["detections"],key=lambda d:-d["confidence"]):
        options=[(iou(pred["bbox_xyxy"],gt["bbox_xyxy"]),j) for j,gt in enumerate(item["boxes"]) if CLASSES[gt["label"]]==pred["class"] and j not in used]
        overlap,j=max(options,default=(0,-1))
        if overlap>=.5:counts[pred["class"]]["tp"]+=1;used.add(j)
        else:
            counts[pred["class"]]["fp"]+=1
            errors.append({'image':item['image'],'prediction':pred,'best_same_class_iou':overlap})
    for j,gt in enumerate(item["boxes"]):
        if j not in used:counts[CLASSES[gt["label"]]]["fn"]+=1
for name,c in counts.items():
    c["precision"]=c["tp"]/max(1,c["tp"]+c["fp"]);c["recall"]=c["tp"]/max(1,c["tp"]+c["fn"])
import numpy as np
report={"domain":('Unseen rendered test views in the same authored scene' if args.split=='test' else 'Rendered development validation'),"iou_threshold":.5,"counts":dict(counts),"inference_p95_ms":float(np.percentile(durations,95)),"images":len(durations)}
report['backend']=args.backend
report['device']=args.device
report['dataset']=str(args.dataset);report['models']=str(args.models);report['split']=args.split
report['kind']=args.kind;report['confidence']=args.confidence
report['false_positive_examples']=errors[:100]
report['input_size']=args.size if args.backend=='onnx' else None
report['primary_size']=args.primary_size or args.size
suffix=f'-primary{args.primary_size}' if args.primary_size else ''
if args.device!='cpu':suffix+='-'+args.device
if args.dataset.name!='synthetic':suffix+='-'+args.dataset.name
if args.split!='val':suffix+='-'+args.split
if args.kind!='both':suffix+='-'+args.kind
if args.confidence!=.35:suffix+='-conf'+str(args.confidence)
(ROOT/f"artifacts/vision-evaluation-{args.backend}-{args.size}{suffix}.json").write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='false_positive_examples'},indent=2))
