"""Bounded simulated vertical takeoff/camera/landing check, no mission claim."""
import json
from pathlib import Path
import time
import math
from skyforge.airsim_rpc import AirSimRPC

ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/airsim';out.mkdir(parents=True,exist_ok=True)
vehicle='SKYFORGE';states=[]
def picture(rpc,name):
    image=rpc.call('simGetImage','front_center',0,vehicle,False)
    if isinstance(image,str):image=image.encode('utf-8','surrogateescape')
    if isinstance(image,list):image=bytes(image)
    (out/name).write_bytes(image)

with AirSimRPC(timeout=25) as rpc:
    if not rpc.call('ping'):raise ConnectionError('AirSim not responding')
    rpc.call('reset')
    rpc.call('simSetCameraPose','front_center',{'position':{'x_val':.7,'y_val':0.,'z_val':-.15},
        'orientation':{'x_val':0.,'y_val':0.,'z_val':0.,'w_val':1.}},vehicle,False)
    rpc.call('enableApiControl',True,vehicle)
    if not rpc.call('armDisarm',True,vehicle):raise RuntimeError('Simulator refused arming')
    try:
        # The packaged level's takeoff position task timed out in testing.
        # Exercise the bounded velocity interface used by an outer controller;
        # do not represent this as a successful takeoff API test.
        rpc.call('moveByVelocity',0.,0.,-1.,2.5,0,{'is_rate':True,'yaw_or_rate':0.},vehicle)
        states.append(rpc.call('getMultirotorState',vehicle))
        rpc.call('hover',vehicle);time.sleep(.5)
        picture(rpc,'hover.png');states.append(rpc.call('getMultirotorState',vehicle))
        if states[-1]['kinematics_estimated']['position']['z_val']> -1.5:raise RuntimeError('Insufficient simulated climb')
    finally:
        try:
            rpc.call('moveByVelocity',0.,0.,.6,6.,0,{'is_rate':True,'yaw_or_rate':0.},vehicle)
            time.sleep(1)
            state=rpc.call('getMultirotorState',vehicle);states.append(state)
            k=state['kinematics_estimated'];speed=math.sqrt(sum(v*v for v in k['linear_velocity'].values()))
            ground=k['position']['z_val']>-.5 and speed<.2
            if ground:rpc.call('armDisarm',False,vehicle)
            else:rpc.call('hover',vehicle)
        finally:
            (out/'flight-smoke.json').write_text(json.dumps({'states':states,'scope':'vertical simulated smoke test only'},indent=2))
    print(json.dumps({'samples':len(states),'ground_position_confirmed':ground,'landed_state':states[-1].get('landed_state'),
        'collided':any(s.get('collision',{}).get('has_collided') for s in states),'image':'artifacts/airsim/hover.png'}))
