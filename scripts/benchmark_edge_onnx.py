"""Quantize candidates and measure CPU inference on the explicitly identified host."""
from pathlib import Path
import hashlib,json,platform,time
from collections import defaultdict
import cv2,numpy as np,onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader,QuantFormat,QuantType,quantize_static
from skyforge.neural_vision import NeuralVisionSystem
from skyforge.scene import CLASSES

ROOT=Path(__file__).resolve().parents[1]

def tensor(path):
    image=cv2.imread(str(path));h,w=image.shape[:2];ratio=min(512/w,512/h)
    rw,rh=round(w*ratio),round(h*ratio);canvas=np.full((512,512,3),114,np.uint8)
    left,top=(512-rw)//2,(512-rh)//2
    canvas[top:top+rh,left:left+rw]=cv2.resize(image,(rw,rh))
    return np.ascontiguousarray(canvas[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255

class Reader(CalibrationDataReader):
    def __init__(self,paths,name):self.items=iter(paths);self.name=name
    def get_next(self):
        p=next(self.items,None)
        return {self.name:tensor(p)} if p else None

def overlap(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def main():
    output=ROOT/'models/edge-int8';output.mkdir(exist_ok=True)
    dataset=ROOT/'data/native-final-v2-test';manifest=json.loads((dataset/'manifest.json').read_text())
    tests=[x for x in manifest if x['split']=='test']
    assert len(tests)==100, 'Expected the declared 100-view comparison set'
    report={'hardware':'AMD Ryzen 5 7535HS, Windows x86-64','platform':platform.platform(),
        'provider':'CPUExecutionProvider','onnxruntime':ort.__version__,'threads_per_model':2,
        'measurement_boundary':'session.run only, excluding preprocessing, NMS, agents and simulator',
        'evaluation_domain':'Existing rendered test views, fixed thresholds, not mAP',
        'cpu_model_measurements':'Separate sequential model sessions, not combined throughput',
        'decision':'Keep FP32 flight baseline; INT8 remains experimental',
        'batch':1,'input':'RGB float32 NCHW 1x3x512x512, letterbox',
        'scope':'Measured laptop CPU inference, not a Raspberry Pi execution or performance prediction',
        'quantization':'Static QDQ S8S8, per-channel Conv weights, MinMax calibration on 32 training images per model',
        'source':'https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html','models':{}}
    for kind,training,ids,threshold in [('primary','yolo_primary-prop-corrected',(1,2,3),.35),('secondary','yolo_secondary-native-v3fast',(4,5),.25)]:
        original=ROOT/'models/native'/(kind+'.onnx');target=output/(kind+'.onnx')
        paths=sorted((ROOT/'data'/training/'images/train').glob('*'))
        paths=[p for p in paths if p.suffix.lower() in ('.jpg','.png','.jpeg')]
        selected=[paths[i] for i in np.linspace(0,len(paths)-1,32,dtype=int)]
        opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
        session=ort.InferenceSession(str(original),sess_options=opts,providers=['CPUExecutionProvider'])
        quantize_static(str(original),str(target),Reader(selected,session.get_inputs()[0].name),quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8,weight_type=QuantType.QInt8,per_channel=True,op_types_to_quantize=['Conv'])
        report['models'][kind]={'calibration_images':[str(p.relative_to(ROOT)) for p in selected],'variants':{}}
        del session
        for variant,path in [('FP32',original),('INT8',target)]:
            session=ort.InferenceSession(str(path),sess_options=opts,providers=['CPUExecutionProvider']);name=session.get_inputs()[0].name
            inputs=[tensor(dataset/x['image']) for x in tests[:25]]
            for i in range(10):session.run(None,{name:inputs[i%len(inputs)]})
            durations=[]
            for i in range(100):
                start=time.perf_counter_ns();session.run(None,{name:inputs[i%len(inputs)]});durations.append((time.perf_counter_ns()-start)/1e6)
            del session
            model=NeuralVisionSystem(path.parent,device='cpu',kinds=(kind,),confidence=threshold)
            counts=defaultdict(lambda:{'tp':0,'fp':0,'fn':0})
            for i,item in enumerate(tests):
                gt=[b for b in item['boxes'] if b['label'] in ids];used=set()
                predictions=model.infer(cv2.imread(str(dataset/item['image'])),{'frame_id':i,'t_sim_ns':0})['detections']
                for pred in sorted(predictions,key=lambda p:-p['confidence']):
                    match=max(((overlap(pred['bbox_xyxy'],b['bbox_xyxy']),j) for j,b in enumerate(gt) if j not in used and CLASSES[b['label']]==pred['class']),default=(0,-1))
                    if match[0]>=.5:counts[pred['class']]['tp']+=1;used.add(match[1])
                    else:counts[pred['class']]['fp']+=1
                for j,b in enumerate(gt):
                    if j not in used:counts[CLASSES[b['label']]]['fn']+=1
            for c in counts.values():
                c['precision']=c['tp']/max(1,c['tp']+c['fp']);c['recall']=c['tp']/max(1,c['tp']+c['fn'])
            model.pool.shutdown();del model
            result={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'warmup':10,'timed_runs':100,'inference_p50_ms':float(np.percentile(durations,50)),
                'inference_p95_ms':float(np.percentile(durations,95)),'evaluation_images':len(tests),
                'confidence':threshold,'iou':.5,'counts':dict(counts)}
            report['models'][kind]['variants'][variant]=result
            print(kind,variant,result['bytes'],result['inference_p50_ms'],result['inference_p95_ms'],flush=True)
    (ROOT/'validation/edge-onnx-benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Report saved; flight models unchanged.',flush=True)

if __name__=='__main__':main()
