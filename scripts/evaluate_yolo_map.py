"""Official Ultralytics box AP on a declared frozen split; never trains weights."""
import argparse
import hashlib
import json
from pathlib import Path
from ultralytics import YOLO
from scripts.train_yolo import prepare

parser=argparse.ArgumentParser()
parser.add_argument('--dataset',type=Path,required=True)
parser.add_argument('--weights',type=Path,required=True)
parser.add_argument('--kind',choices=['primary','secondary'],required=True)
parser.add_argument('--split',choices=['val','test'],default='test')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
data=prepare(args.kind,args.dataset,tag='-frozen-evaluation-'+args.dataset.name)
for split in ('train','val','test'):(data.parent/'images'/split).mkdir(exist_ok=True,parents=True)
result=YOLO(args.weights).val(data=str(data),split=args.split,imgsz=512,batch=4,device=0,
    workers=0,rect=False,plots=False,save_json=False,conf=.001,project='artifacts/map-evaluation',name=args.kind+'-'+args.dataset.name,exist_ok=True)
names=result.names
report={'implementation':'Official Ultralytics box validation, 101-point AP; no training',
    'domain':'Unseen views in the same authored scene; not unseen-world or real-photo generalization',
    'weights_sha256':hashlib.file_digest(args.weights.open('rb'),'sha256').hexdigest(),
    'manifest_sha256':hashlib.file_digest((args.dataset/'manifest.json').open('rb'),'sha256').hexdigest(),
    'split':args.split,'dataset':str(args.dataset),'kind':args.kind,'map50':float(result.box.map50),'map50_95':float(result.box.map),
    'classes':{names[int(index)]:{'ap50':float(result.box.ap50[i]),'ap50_95':float(result.box.ap[i])} for i,index in enumerate(result.box.ap_class_index)}}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
