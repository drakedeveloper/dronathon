"""Visible, bounded physics flight demonstration, independent of rescue AI."""
import json
import math
from pathlib import Path
import time
from skyforge.airsim_rpc import AirSimRPC

vehicle='SKYFORGE';out=Path(__file__).resolve().parents[1]/'artifacts/airsim'
out.mkdir(parents=True,exist_ok=True);trace=[]
deadline=time.monotonic()+60
while True:
    try:
        with AirSimRPC(timeout=2) as rpc:
            if rpc.call('ping'):break
    except (OSError,ValueError):
        if time.monotonic()>deadline:raise TimeoutError('AirSim did not start')
        time.sleep(1)

with AirSimRPC(timeout=4) as rpc:
    settings=json.loads(rpc.call('getSettingsString'))
    if settings.get('PhysicsEngineName')=='ExternalPhysicsEngine':
        raise RuntimeError('Close scenic preview and launch start-airsim.ps1 without -Scenic')
    rpc.call('simRunConsoleCommand','t.MaxFPS 30')
    rpc.call('enableApiControl',True,vehicle)
    initial=rpc.call('getMultirotorState',vehicle)
    home=initial['kinematics_estimated']['position']
    home_xyz=[home[k] for k in ('x_val','y_val','z_val')]
    if not rpc.call('armDisarm',True,vehicle):raise RuntimeError('Simulator refused arming')
    collision_at_start=initial['collision']['time_stamp']
    def sample():
        state=rpc.call('getMultirotorState',vehicle)
        trace.append(state)
        if state['collision']['has_collided'] and state['collision']['time_stamp']>collision_at_start:
            raise RuntimeError('New simulated contact detected; stopping route')
        return state
    def velocity(vx,vy,vz,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rpc.call('moveByVelocity',float(vx),float(vy),float(vz),.2,0,
                     {'is_rate':True,'yaw_or_rate':0.},vehicle)
            sample()
    try:
        print('Taking off: physical rotor simulation, chase camera',flush=True)
        velocity(0,0,-1.,8.)
        print('Moving forward',flush=True);velocity(.65,0,0,5.)
        print('Moving sideways',flush=True);velocity(0,.5,0,3.)
        print('Returning over launch area',flush=True)
        for _ in range(100):
            state=sample();p=state['kinematics_estimated']['position']
            dx=home_xyz[0]-p['x_val'];dy=home_xyz[1]-p['y_val']
            if math.hypot(dx,dy)<.25:break
            rpc.call('moveByVelocity',max(-.7,min(.7,.8*dx)),max(-.7,min(.7,.8*dy)),0.,.2,0,
                     {'is_rate':True,'yaw_or_rate':0.},vehicle)
        print('Hovering above launch point',flush=True);velocity(0,0,0,3.)
    finally:
        # Descend in short bounded commands; verify ground/low speed before
        # disarming rather than trusting this old binary's landed_state alone.
        print('Landing',flush=True);ground=False
        try:
            for _ in range(120):
                state=rpc.call('getMultirotorState',vehicle);trace.append(state)
                k=state['kinematics_estimated'];p=k['position'];v=k['linear_velocity']
                near=abs(p['z_val']-home_xyz[2])<.25
                speed=math.sqrt(sum(v[a]**2 for a in ('x_val','y_val','z_val')))
                if near and speed<.2:
                    ground=True;rpc.call('armDisarm',False,vehicle);break
                rpc.call('moveByVelocity',0.,0.,.55,.2,0,{'is_rate':True,'yaw_or_rate':0.},vehicle)
            if not ground:rpc.call('hover',vehicle)
        finally:
            (out/'visible-flight.json').write_text(json.dumps({'mode':'physics flight demonstration, no rescue AI',
                'ground_return_confirmed':ground,'trace':trace},indent=2))
    print(f'Flight complete; ground return confirmed={ground}',flush=True)
