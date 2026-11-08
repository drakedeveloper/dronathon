"""Read-only camera/pose calibration probe; never arms or moves a vehicle."""
import json
import argparse
from pathlib import Path
import time
import cv2
import numpy as np
from skyforge.airsim_backend import AirSimBackend

root=Path(__file__).resolve().parents[1];out=root/'artifacts/airsim';out.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=41461)
args=parser.parse_args();backend=AirSimBackend(port=args.port)
try:
    start=time.perf_counter();frame=backend.frame();pose=frame['pose']
    report={'camera_pose_probe_ms':(time.perf_counter()-start)*1000,'rgb_size':list(frame['image'].shape),
            'depth_size':list(frame['depth'].shape),'valid_depth_fraction':float(np.isfinite(frame['depth']).mean()),
            'p_enu_m':pose['p'].tolist(),'q_enu_flu_xyzw':pose['q'].tolist(),
            'scope':'Read-only sensor/frame alignment probe; no rescue mission or control authorization'}
    cv2.imwrite(str(out/'native-downward.jpg'),frame['image'])
    (out/'native-sensor-probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:backend.close()
