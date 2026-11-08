"""Offline, calibrated prior imagery from the actual scene; never move the drone.

Run only after all flight/scenario services stop. Temporarily conceal mission
entities, capture static site imagery, then restore every object and camera.
The imagery is a station backdrop and is never supplied to the agents.
"""
import json
import math
from pathlib import Path
import time
import cv2
import numpy as np
from skyforge.airsim_backend import AirSimBackend,binary_data,vector_xyz,quaternion_xyzw
from skyforge.geometry import rotation_xyzw
from skyforge.scene import ROOT


def quaternion(matrix):
    vector,_=cv2.Rodrigues(matrix);angle=float(np.linalg.norm(vector))
    return np.r_[vector.ravel()/angle*math.sin(angle/2),math.cos(angle/2)] if angle>1e-10 else np.array([0,0,0,1])


def main():
    backend=AirSimBackend(port=41461);rpc=backend.commands;rpc.timeout=15.;backend.camera.timeout=15.
    deadline=time.monotonic()+60
    while True:
        try:state=rpc.call('getMultirotorState','SKYFORGE');break
        except OSError:
            if time.monotonic()>deadline:raise
            time.sleep(.5)
    kin=state['kinematics_estimated']
    if np.linalg.norm(vector_xyz(kin['linear_velocity']))>.1 or state.get('landed_state')!=0:
        raise RuntimeError('Static imagery requires a landed stationary vehicle and stopped flight services')
    settings=json.loads(rpc.call('getSettingsString'));spawn=settings['Vehicles']['SKYFORGE']
    manifest=json.loads((ROOT/'configs/scenes/native-scene-manifest.json').read_text())
    output=ROOT/'station/dist/assets';output.mkdir(exist_ok=True)
    hidden=[];camera=settings['Vehicles']['SKYFORGE']['Cameras']['front_center']
    position=vector_xyz(kin['position']);rotation=rotation_xyzw(quaternion_xyzw(kin['orientation']))
    desired=rotation_xyzw([0,-math.sqrt(.5),0,math.sqrt(.5)])
    orientation=quaternion(rotation.T@desired)
    def pose(offset,q):return {'position':dict(zip(('x_val','y_val','z_val'),map(float,offset))),
                              'orientation':dict(zip(('x_val','y_val','z_val','w_val'),map(float,q)))}
    records=[]
    try:
        for entity in manifest['annotation_entities']:
            for name in entity['actor_names']:
                original=rpc.call('simGetObjectScale',name)
                if not rpc.call('simSetObjectScale',name,{'x_val':.00001,'y_val':.00001,'z_val':.00001}):raise RuntimeError('Cannot conceal '+name)
                hidden.append((name,original))
                if max(vector_xyz(rpc.call('simGetObjectScale',name)))>.0001:raise RuntimeError('Object scale concealment failed')
        for name,span in [('site',256.),('mission',64.)]:
            altitude=span*.75;fov=math.degrees(2*math.atan(span/(2*altitude)))
            desired_position=np.array([-spawn['X'],-spawn['Y'],-altitude+(-spawn['Z'])])
            offset=rotation.T@(desired_position-position)
            rpc.call('simSetCameraPose','front_center',pose(offset,orientation),'SKYFORGE')
            rpc.call('simSetCameraFov','front_center',fov,'SKYFORGE')
            time.sleep(.3)
            request=[{'camera_name':'front_center','image_type':0,'pixels_as_float':False,'compress':True}]
            backend.images(request);result=backend.images(request)[0]
            image=cv2.imdecode(np.frombuffer(binary_data(result['image_data_uint8']),np.uint8),cv2.IMREAD_COLOR)
            if image is None:raise RuntimeError('Invalid prior imagery')
            info=rpc.call('simGetCameraInfo','front_center','SKYFORGE')
            cv2.imwrite(str(output/(name+'-aerial.jpg')),image,[cv2.IMWRITE_JPEG_QUALITY,94])
            records.append({'file':name+'-aerial.jpg','bounds_enu_m':[-span/2,-span*image.shape[0]/image.shape[1]/2,span/2,span*image.shape[0]/image.shape[1]/2],
                            'camera':info,'image_size_wh':[image.shape[1],image.shape[0]],'scope':'Static prior render, mission entities concealed; ground-plane projection, relief displacement on hills'})
    finally:
        for name,original in reversed(hidden):rpc.call('simSetObjectScale',name,original)
        rpc.call('simSetCameraPose','front_center',pose([camera['X'],camera['Y'],camera['Z']],[0,0,0,1]),'SKYFORGE')
        rpc.call('simSetCameraFov','front_center',camera['CaptureSettings'][0]['FOV_Degrees'],'SKYFORGE')
        backend.close()
    (output/'aerial-calibration.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(records,indent=2))


if __name__=='__main__':main()
