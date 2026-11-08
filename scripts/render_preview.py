"""Bounded independent scene render; never use stale images as success evidence."""
import os
import signal
import subprocess
import time
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
os.environ['GZ_PARTITION']='skyforge-preview'
os.environ['GZ_SIM_RESOURCE_PATH']=str(ROOT/'sim/models')
os.environ['GZ_SIM_SYSTEM_PLUGIN_PATH']='/opt/skyforge/plugins'
from skyforge.scene import create_world
from skyforge.transport import GazeboBus
from gz.msgs10.image_pb2 import Image

path,_=create_world()
captured=[]
def callback(message):
    channels=message.step//message.width
    array=np.frombuffer(message.data,dtype=np.uint8).reshape(message.height,message.width,channels)
    captured.append(cv2.cvtColor(array[:,:,:3],cv2.COLOR_RGB2BGR))
bus=GazeboBus(camera_enabled=False)
bus.node.subscribe(Image,'/skyforge/observer',callback)
with (ROOT/'artifacts/preview.log').open('w') as log:
    proc=subprocess.Popen(['gz','sim','-s','-r','-v','2',str(path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        deadline=time.monotonic()+50
        while len(captured)<3 and time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('Renderer exited; see artifacts/preview.log')
            time.sleep(.2)
        if not captured:raise TimeoutError('No fresh rendered image within 50 seconds')
        cv2.imwrite(str(ROOT/'artifacts/coast-preview.jpg'),captured[-1])
        print('Fresh preview: artifacts/coast-preview.jpg',flush=True)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGINT)
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
