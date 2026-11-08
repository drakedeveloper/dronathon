"""Two exported YOLO11 detectors using bounded CPU ONNX inference.

Explicit opt-in until scene-domain evaluation and latency checks pass. No
training dependency, Torch, network request or annotation access at inference.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
import onnxruntime as ort


class NeuralVisionSystem:
    def __init__(self,models_dir,confidence=.35,size=512,primary_size=None,spinning=False,device='cpu',kinds=('primary','secondary')):
        if not kinds or any(kind not in ('primary','secondary') for kind in kinds):raise ValueError('Invalid detector selection')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry('session.intra_op.allow_spinning','1' if spinning else '0')
        options.add_session_config_entry('session.inter_op.allow_spinning','1' if spinning else '0')
        if size not in (384,512):raise ValueError('Unsupported detector input size')
        self.size=size
        self.sizes={'primary':primary_size or size,'secondary':size}
        if any(s not in (384,512) for s in self.sizes.values()):raise ValueError('Unsupported detector input size')
        self.models=[];self.confidence=confidence;self.pool=ThreadPoolExecutor(max_workers=2)
        providers=['CPUExecutionProvider']
        if device=='cuda':
            if hasattr(ort,'preload_dlls'):ort.preload_dlls(directory='')
            if 'CUDAExecutionProvider' not in ort.get_available_providers():raise RuntimeError('CUDA inference provider unavailable')
            providers=[('CUDAExecutionProvider',{'gpu_mem_limit':384*1024**2,'arena_extend_strategy':'kSameAsRequested',
                'cudnn_conv_algo_search':'HEURISTIC','cudnn_conv_use_max_workspace':'0','do_copy_in_default_stream':'1'}),
                'CPUExecutionProvider']
        elif device!='cpu':raise ValueError('Unsupported inference device')
        self.device=device
        for kind,names in (('primary',['waste','mine','weapon']),('secondary',['injured_person','hostile_unit'])):
            if kind not in kinds:continue
            model_size=self.sizes[kind]
            suffix='-384' if model_size==384 else ''
            session=ort.InferenceSession(str(Path(models_dir)/(kind+suffix+'.onnx')),sess_options=options,providers=providers)
            if device=='cuda' and session.get_providers()[0]!='CUDAExecutionProvider':raise RuntimeError('CUDA session fell back to CPU')
            if session.get_inputs()[0].shape[-2:]!=[model_size,model_size]:raise ValueError('Detector input dimensions mismatch')
            self.models.append((kind,names,session))

    def infer(self,image_bgr,frame_meta,secondary_zoom_out=False):
        h,w=image_bgr.shape[:2];inputs={}
        for size in set(self.sizes.values()):
            ratio=min(size/w,size/h);rw,rh=round(w*ratio),round(h*ratio)
            left=(size-rw)//2;top=(size-rh)//2
            canvas=np.full((size,size,3),114,np.uint8)
            canvas[top:top+rh,left:left+rw]=cv2.resize(image_bgr,(rw,rh))
            tensor=np.ascontiguousarray(canvas[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255
            inputs[size]=(tensor,ratio,left,top)
        secondary_input=None
        if secondary_zoom_out:
            size=self.sizes['secondary'];ratio=min(size/w,size/h)*.5
            rw,rh=round(w*ratio),round(h*ratio);left=(size-rw)//2;top=(size-rh)//2
            canvas=np.full((size,size,3),114,np.uint8);canvas[top:top+rh,left:left+rw]=cv2.resize(image_bgr,(rw,rh))
            secondary_input=(np.ascontiguousarray(canvas[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255,ratio,left,top)
        detections=[]
        selected_inputs={kind:secondary_input if kind=='secondary' and secondary_input is not None else inputs[self.sizes[kind]] for kind,_,_ in self.models}
        futures=[]
        for kind,_,session in self.models:
            metadata=session.get_inputs()[0]
            dtype=np.float16 if getattr(metadata,'type','tensor(float)')=='tensor(float16)' else np.float32
            tensor=selected_inputs[kind][0].astype(dtype,copy=False)
            futures.append(self.pool.submit(session.run,None,{metadata.name:tensor}))
        for (kind,names,session),future in zip(self.models,futures):
            _,ratio,left,top=selected_inputs[kind]
            output=future.result()[0]
            rows=output[0].T
            if rows.shape[1]!=4+len(names):raise ValueError('Unexpected ONNX output layout')
            scores=rows[:,4:];labels=scores.argmax(axis=1);confidence=scores.max(axis=1)
            for label,name in enumerate(names):
                selected=(labels==label)&(confidence>=self.confidence)
                proposals=rows[selected,:4];values=confidence[selected]
                if not len(proposals):continue
                boxes=np.c_[(proposals[:,0]-proposals[:,2]/2-left)/ratio,
                            (proposals[:,1]-proposals[:,3]/2-top)/ratio,
                            proposals[:,2]/ratio,proposals[:,3]/ratio]
                keep=cv2.dnn.NMSBoxes(boxes.tolist(),values.tolist(),self.confidence,.45)
                for index in np.asarray(keep).reshape(-1):
                    x,y,bw,bh=boxes[index]
                    box=[float(np.clip(x,0,w)),float(np.clip(y,0,h)),float(np.clip(x+bw,0,w)),float(np.clip(y+bh,0,h))]
                    if box[2]<=box[0] or box[3]<=box[1]:continue
                    detections.append({'class':name,'confidence':float(values[index]),'bbox_xyxy':box,'source':kind})
        return {'v':1,'frame_id':int(frame_meta['frame_id']),'t_sim_ns':int(frame_meta['t_sim_ns']),
                'camera_id':frame_meta.get('camera_id','downward_rgb'),'image_size_wh':[w,h],'detections':detections}
