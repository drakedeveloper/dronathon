"""Fast learned pixel/region detector and replaceable model boundary.

The bootstrap model is trained from rendered RGB/annotation pairs, and is
scene-domain-specific. It is not represented as a general real-world detector.
"""
from pathlib import Path
import json
import time
import cv2
import numpy as np
from .scene import CLASSES
from .geometry import rotation_xyzw


def features(bgr):
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    return np.concatenate([bgr,hsv],axis=2).reshape(-1,6).astype(np.float32)


HOG=cv2.HOGDescriptor((32,32),(16,16),(8,8),(8,8),9)


def region_features(crop):
    if crop.size==0:return None
    resized=cv2.resize(crop,(32,32))
    hog=HOG.compute(cv2.cvtColor(resized,cv2.COLOR_BGR2GRAY)).ravel()
    hsv=cv2.cvtColor(resized,cv2.COLOR_BGR2HSV)
    hist=[]
    for i,bins,upper in ((0,18,180),(1,8,256),(2,8,256)):
        counts=cv2.calcHist([hsv],[i],None,[bins],[0,upper]).ravel();hist.extend(counts/max(1,counts.sum()))
    return np.r_[hog,hist,np.clip(crop.shape[1]/crop.shape[0],0,8)/8].astype(np.float32)


class VisionSystem:
    def __init__(self,models_dir,device="cpu",use_verifier=True):
        folder=Path(models_dir)
        self.model=cv2.ml.RTrees_load(str(folder/"pixel_forest.xml"))
        if not self.model.isTrained(): raise RuntimeError("Vision model is not trained")
        self.model_info=json.loads((folder/"model-card.json").read_text())
        self.verifier=cv2.ml.SVM_load(str(folder/"region_svm.xml")) if use_verifier and (folder/"region_svm.xml").exists() else None

    def infer(self,image_bgr,frame_meta):
        start=time.perf_counter_ns()
        h,w=image_bgr.shape[:2]
        sw,sh=max(1,w//3),max(1,h//3)
        small=cv2.resize(image_bgr,(sw,sh),interpolation=cv2.INTER_AREA)
        raw=self.model.predict(features(small))[1].reshape(sh,sw).astype(np.uint8)
        detections=[]
        for label,name in CLASSES.items():
            mask=(raw==label).astype(np.uint8)*255
            mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
            mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
            count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
            for i in range(1,count):
                x,y,bw,bh,area=stats[i]
                if area<12 or bw<3 or bh<3: continue
                if area>sw*sh*.15: continue
                # Empirical component confidence, not calibrated probability.
                confidence=float(np.clip(.45+.5*area/(bw*bh),0,1))
                box=[max(0,float(x*w/sw-2)),max(0,float(y*h/sh-2)),
                     min(float(w),float((x+bw)*w/sw+2)),min(float(h),float((y+bh)*h/sh+2))]
                if self.verifier is not None and label not in (1,2):
                    x0,y0,x1,y1=map(int,box);vector=region_features(image_bgr[y0:y1,x0:x1])
                    if vector is None or int(self.verifier.predict(vector[None,:])[1][0,0])!=label:continue
                detections.append({"class":name,"confidence":confidence,"bbox_xyxy":box,
                                   "source":"secondary" if label>=4 else "primary"})
        return {"v":1,"frame_id":int(frame_meta["frame_id"]),"t_sim_ns":int(frame_meta["t_sim_ns"]),
                "camera_id":frame_meta.get("camera_id","downward_rgb"),"image_size_wh":[w,h],"detections":detections}


def train_forest(dataset_dir,models_dir):
    folder=Path(dataset_dir); output=Path(models_dir); output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((folder/"manifest.json").read_text())
    rng=np.random.default_rng(2026); rows=[]; targets=[]
    for item in manifest:
        if item["split"]!="train": continue
        image=cv2.imread(str(folder/item["image"]))
        h,w=image.shape[:2]; f=features(image).reshape(h,w,6)
        occupied=np.zeros((h,w),bool)
        for box in item["boxes"]:
            x0,y0,x1,y1=map(int,box["bbox_xyxy"])
            occupied[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]=True
        background=f[~occupied]
        background_median=np.median(background[:,:3],axis=0) if len(background) else np.zeros(3)
        for box in item["boxes"]:
            x0,y0,x1,y1=map(int,box["bbox_xyxy"])
            x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
            if x1<=x0 or y1<=y0: continue
            occupied[y0:y1,x0:x1]=True
            # Interior pixels reduce background contamination in object boxes.
            dx=max(0,(x1-x0)//6);dy=max(0,(y1-y0)//6)
            patch=f[y0+dy:y1-dy or y1,x0+dx:x1-dx or x1].reshape(-1,6)
            if not len(patch): continue
            # Bounding boxes include background: select the dominant rendered
            # foreground appearance instead of teaching sand as casualty pixels.
            patch=patch[np.linalg.norm(patch[:,:3]-background_median,axis=1)>45]
            if len(patch)>12:
                sample=patch[rng.choice(len(patch),min(1500,len(patch)),replace=False)]
                _,labels,centers=cv2.kmeans(sample[:,:3].copy(),2,None,(cv2.TERM_CRITERIA_MAX_ITER,20,.5),3,cv2.KMEANS_PP_CENTERS)
                counts=np.bincount(labels.ravel(),minlength=2)
                chosen=int(np.argmax(counts*np.linalg.norm(centers-background_median,axis=1)))
                center=centers[chosen]
                distances=np.linalg.norm(patch[:,:3]-center,axis=1)
                patch=patch[distances<max(18,float(np.percentile(distances,60)))]
            if not len(patch):continue
            sample=patch[rng.choice(len(patch),min(250,len(patch)),replace=False)]
            rows.append(sample); targets.extend([box["label"]]*len(sample))
        candidates=f[~occupied]
        if len(candidates):
            sample=candidates[rng.choice(len(candidates),min(600,len(candidates)),replace=False)]
            rows.append(sample);targets.extend([0]*len(sample))
    if not rows: raise ValueError("No rendered training samples")
    x=np.vstack(rows); y=np.asarray(targets,np.int32)
    model=cv2.ml.RTrees_create();model.setMaxDepth(12);model.setMinSampleCount(5)
    model.setMaxCategories(6);model.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,24,0))
    start=time.perf_counter(); model.train(x,cv2.ml.ROW_SAMPLE,y);model.save(str(output/"pixel_forest.xml"))
    card={"model":"rendered-domain pixel random forest", "features":"BGR + HSV", "trees":24,
          "training_pixels":len(y),"training_images":sum(i["split"]=="train" for i in manifest),
          "classes":{"0":"background",**{str(k):v for k,v in CLASSES.items()}},
          "training_seconds":time.perf_counter()-start,
          "limitations":["Appearance/role cues specific to declared synthetic scene", "Not a general photographic hazard or injury detector", "Confidence is a component heuristic, not calibrated probability"],
          "data_source":"Rendered Gazebo RGB; annotation boxes used only during training/evaluation"}
    (output/"model-card.json").write_text(json.dumps(card,indent=2))
    # A second learned stage checks shape/context and rejects dark scenery or
    # disconnected clothing fragments that share a foreground color.
    vectors=[];classes=[]
    for item in manifest:
        if item["split"]!="train":continue
        image=cv2.imread(str(folder/item["image"]));h,w=image.shape[:2]
        for box in item["boxes"]:
            a,b,c,d=map(int,box["bbox_xyxy"])
            for expansion in (0.,.08,.16):
                dx=int((c-a)*expansion);dy=int((d-b)*expansion)
                crop=image[max(0,b-dy):min(h,d+dy),max(0,a-dx):min(w,c+dx)]
                vector=region_features(crop)
                if vector is not None:vectors.append(vector);classes.append(box["label"])
        for _ in range(12):
            bw=int(rng.integers(16,150));bh=int(rng.integers(12,110));a=int(rng.integers(0,w-bw));b=int(rng.integers(0,h-bh))
            overlap=False
            for box in item["boxes"]:
                x0,y0,x1,y1=box["bbox_xyxy"]
                if max(0,min(a+bw,x1)-max(a,x0))*max(0,min(b+bh,y1)-max(b,y0))>0:overlap=True;break
            if not overlap:vectors.append(region_features(image[b:b+bh,a:a+bw]));classes.append(0)
    svm=cv2.ml.SVM_create();svm.setType(cv2.ml.SVM_C_SVC);svm.setKernel(cv2.ml.SVM_RBF);svm.setC(12);svm.setGamma(.4)
    svm.train(np.vstack(vectors),cv2.ml.ROW_SAMPLE,np.asarray(classes,np.int32));svm.save(str(output/"region_svm.xml"))
    card["region_verifier"]={"model":"HOG/HSV RBF SVM","training_regions":len(classes)}
    (output/"model-card.json").write_text(json.dumps(card,indent=2));return card


def localize(detection,frame):
    if frame["pose"] is None or frame["depth"] is None: return None
    image=frame["image"]; depth=frame["depth"]; h,w=image.shape[:2]
    x0,y0,x1,y1=detection["bbox_xyxy"];u=(x0+x1)/2;v=(y0+y1)/2
    patch=depth[max(0,int(v)-2):min(h,int(v)+3),max(0,int(u)-2):min(w,int(u)+3)]
    valid=patch[np.isfinite(patch)&(patch>0)&(patch<60)]
    if len(valid)<3:return None
    z=float(np.median(valid)); fx=w/(2*np.tan(.6));fy=fx
    p_opt=np.array([(u-(w-1)/2)*z/fx,(v-(h-1)/2)*z/fy,z])
    # GZ camera looks along +X; optical axes right/down/forward.
    pitch=np.array([[0,0,1],[0,1,0],[-1,0,0]],float)
    optical_to_camera=np.array([[0,0,1],[-1,0,0],[0,-1,0]],float)
    rotation=rotation_xyzw(frame["pose"]["q"])
    world=frame["pose"]["p"]+rotation@(np.array([0,0,-.12])+pitch@optical_to_camera@p_opt)
    return world


def ground_depth_difference(position,frame):
    """Optical depth above the expected flat ground, or unknown outside view."""
    if frame.get('pose') is None or frame.get('depth') is None:return None
    h,w=frame['image'].shape[:2]
    body=rotation_xyzw(frame['pose']['q']).T@(np.asarray(position)-frame['pose']['p'])-np.array([0,0,-.12])
    optical=np.array([-body[1],-body[0],-body[2]])
    if optical[2]<=.1:return None
    focal=w/(2*np.tan(.6));u=focal*optical[0]/optical[2]+(w-1)/2;v=focal*optical[1]/optical[2]+(h-1)/2
    if not(12<=u<w-12 and 12<=v<h-12):return None
    patch=frame['depth'][int(v)-2:int(v)+3,int(u)-2:int(u)+3]
    valid=patch[np.isfinite(patch)&(patch>0)]
    return float(optical[2]-np.median(valid)) if len(valid)>=3 else None


def ground_point_visible(position,frame):
    """Negative evidence requires empty ground, not a low lying person."""
    difference=ground_depth_difference(position,frame)
    return difference is not None and abs(difference)<.075
