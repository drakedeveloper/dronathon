"""Aerial spectator preview. Teleports a rendering camera, not a flight demo."""
import json
import math
from pathlib import Path
import time
from skyforge.airsim_rpc import AirSimRPC

out=Path(__file__).resolve().parents[1]/'artifacts/airsim';out.mkdir(parents=True,exist_ok=True)
deadline=time.monotonic()+60
while True:
    try:
        with AirSimRPC(timeout=2) as rpc:
            if rpc.call('ping'):break
    except (OSError,ValueError):
        if time.monotonic()>deadline:raise TimeoutError('AirSim did not become ready')
        time.sleep(1)

def quaternion(pitch=0,yaw=0):
    p=math.radians(pitch)/2;y=math.radians(yaw)/2
    return {'x_val':-math.sin(p)*math.sin(y),'y_val':math.sin(p)*math.cos(y),
            'z_val':math.cos(p)*math.sin(y),'w_val':math.cos(p)*math.cos(y)}

with AirSimRPC(timeout=10) as rpc:
    settings=json.loads(rpc.call('getSettingsString'))
    if settings.get('PhysicsEngineName')!='ExternalPhysicsEngine':
        raise RuntimeError('Start with start-airsim.ps1 -Scenic; this preview uses camera teleportation')
    rpc.call('simRunConsoleCommand','t.MaxFPS 30')
    rpc.call('simRunConsoleCommand','sg.ShadowQuality 2')
    rpc.call('simRunConsoleCommand','sg.PostProcessQuality 2')
    rpc.call('simRunConsoleCommand','sg.TextureQuality 2')
    rpc.call('simSetVehiclePose',{'position':{'x_val':0.,'y_val':0.,'z_val':-90.},'orientation':quaternion()},True,'SKYFORGE')
    for yaw in (0,90,180,270):
        pose={'position':{'x_val':.7,'y_val':0.,'z_val':-.15},'orientation':quaternion(-35,yaw)}
        rpc.call('simSetCameraPose','front_center',pose,'SKYFORGE',False);time.sleep(.7)
        image=rpc.call('simGetImage','front_center',0,'SKYFORGE',False)
        if isinstance(image,str):image=image.encode('utf-8','surrogateescape')
        if isinstance(image,list):image=bytes(image)
        (out/f'scenic-{yaw}.png').write_bytes(image)
    rpc.call('simSetCameraPose','front_center',{'position':{'x_val':.7,'y_val':0.,'z_val':-.15},
             'orientation':quaternion(-35,0)},'SKYFORGE',False)
    print('AirSim aerial spectator preview ready; images in artifacts/airsim/scenic-*.png',flush=True)
