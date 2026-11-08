import json
import os
from pathlib import Path
import signal
import subprocess
import time
from skyforge.scene import create_world,ROOT
from skyforge.transport import GazeboBus

out=ROOT/"artifacts"/"scene-probe"; out.mkdir(exist_ok=True)
path,_=create_world(dataset=True)
log=(out/"server.log").open("w")
process=subprocess.Popen(["gz","sim","-s","-r","-v","2",str(path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
try:
    bus=GazeboBus(annotations=True)
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        frame=bus.frame()
        if frame is not None and bus.boxes is not None:
            import cv2
            cv2.imwrite(str(out/"camera.jpg"),frame["image"])
            print("RGB",frame["image"].shape,"depth",None if frame["depth"] is None else frame["depth"].shape)
            print("BOXES",str(bus.boxes)[:4500])
            time.sleep(2)
            print("SERVICES",bus.node.service_list())
            print("MOVE",bus.set_camera_pose(5,5,6))
            r=subprocess.run(["gz","service","-s","/world/skyforge/set_pose","--reqtype","gz.msgs.Pose","--reptype","gz.msgs.Boolean","--timeout","3000","--req",'name: "dataset_camera" position: {x: 5 y: 5 z: 6} orientation: {w: 1}'],capture_output=True,text=True)
            print("CLI MOVE",r.returncode,r.stdout,r.stderr)
            break
        time.sleep(.1)
    else: raise RuntimeError(f"No camera/annotations: {bus.errors}")
finally:
    os.killpg(process.pid,signal.SIGINT)
    process.wait(timeout=15); log.close()
