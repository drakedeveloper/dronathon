"""Simulator-only weather/kinematic prop driver. Does not publish target truth."""
import argparse
import json
import math
from pathlib import Path
import signal
import time
from .airsim_rpc import AirSimRPC


def scenario_wind(t):
    transition=.5*(1+math.tanh((t-45)/3))
    return [.7-transition+.25*math.sin(t*.31),.25+.2*math.sin(t*.19),0.]


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config',type=Path);args=parser.parse_args()
    config=json.loads(args.config.read_text());manifest=json.loads(Path(config['scene_manifest']).read_text())
    running=True
    def stop(*_):
        global running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    with AirSimRPC(port=config['api_port'],timeout=2) as rpc:
        start=None;last=-1.
        while running:
            state=rpc.call('getMultirotorState','SKYFORGE');absolute=state['timestamp']/1e9
            if start is None:start=absolute
            t=absolute-start
            if t-last>.15:
                wind=scenario_wind(t)
                rpc.call('simSetWind',{'x_val':wind[1],'y_val':wind[0],'z_val':-wind[2]})
                # Oscillating mast replaces the prototype's unbounded moving
                # column. Only lidar/camera may expose it to mission planning.
                x=3*math.sin(t*.18);enu=[x,-6,3.5]
                rpc.call('simSetObjectPose',manifest['moving_obstacle_actor'],{
                    'position':{'x_val':enu[1],'y_val':enu[0],'z_val':-enu[2]},
                    'orientation':{'x_val':0.,'y_val':0.,'z_val':0.,'w_val':1.}},True)
                last=t
            time.sleep(.05)
