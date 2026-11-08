"""Capture real simulator RGB + visible-box annotations in separate dataset mode."""
from pathlib import Path
import json
import os
import signal
import subprocess
import time
import cv2
import numpy as np
from skyforge.scene import create_world,ROOT
from skyforge.transport import GazeboBus,stamp
from skyforge.vision import train_forest

out=ROOT/"data"/"synthetic"; (out/"images").mkdir(parents=True,exist_ok=True)
manifest=[];rng=np.random.default_rng(340)
# Scene seeds, not adjacent video frames, define the split.
for split,seed,count in [("train",11,70),("val",22,20),("test",33,10)]:
    path,scene=create_world(seed,dataset=True)
    log=(out/f"{split}-server.log").open("w")
    proc=subprocess.Popen(["gz","sim","-s","-r","-v","1",str(path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        bus=GazeboBus(annotations=True)
        deadline=time.monotonic()+40
        while (bus.frame() is None or bus.boxes is None) and time.monotonic()<deadline: time.sleep(.1)
        if bus.frame() is None: raise RuntimeError("No synthetic camera")
        for index in range(count):
            entity=scene["entities"][index%len(scene["entities"])]
            x,y,_=entity["position"]
            if index%10==0:x,y=-12,-9
            elif index%10==1:x,y=5,4
            x+=float(rng.uniform(-1.5,1.5));y+=float(rng.uniform(-1.5,1.5))
            old_t=bus.sim_time
            ok,_=bus.set_camera_pose(x,y,float(rng.uniform(4.5,8.5)))
            if not ok: raise RuntimeError("Dataset camera move failed")
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                frame=bus.frame(); boxes=bus.boxes
                if frame and frame["t"]>old_t+.12 and boxes is not None and abs(stamp(boxes)-frame["t"])<.06: break
                time.sleep(.025)
            else: raise RuntimeError("Dataset image/annotation synchronization timeout")
            annotations=[]
            for entry in boxes.annotated_box:
                if entry.label not in range(1,6):continue
                b=entry.box
                coords=[float(b.min_corner.x),float(b.min_corner.y),float(b.max_corner.x),float(b.max_corner.y)]
                if coords[2]-coords[0]<4 or coords[3]-coords[1]<4:continue
                annotations.append({"label":entry.label,"bbox_xyxy":coords})
            name=f"images/{split}-{index:04}.jpg"
            cv2.imwrite(str(out/name),frame["image"],[cv2.IMWRITE_JPEG_QUALITY,92])
            manifest.append({"image":name,"split":split,"scene_seed":seed,"frame_time":frame["t"],"boxes":annotations})
            if index%10==0:print(split,index,"boxes",len(annotations),flush=True)
    finally:
        del bus
        os.killpg(proc.pid,signal.SIGINT);proc.wait(timeout=15);log.close();time.sleep(1)
(out/"manifest.json").write_text(json.dumps(manifest,indent=2))
print(json.dumps(train_forest(out,ROOT/"models"),indent=2))
