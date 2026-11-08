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


def scenario_fog(t):
    """Declared renderer fog strength, not an estimated visibility in metres."""
    return .02+.10*.5*(1+math.tanh((t-45)/6))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config',type=Path);args=parser.parse_args()
    config=json.loads(args.config.read_text());manifest=json.loads(Path(config['scene_manifest']).read_text())
    running=True
    def stop(*_):
        global running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    with AirSimRPC(port=config['api_port'],timeout=2) as rpc:
        start=None;last=-1.;errors=0;weather_enabled=False
        while running:
            try:state=rpc.call('getMultirotorState','SKYFORGE');absolute=state['timestamp']/1e9
            except (OSError,ValueError,RuntimeError) as error:
                errors+=1;print('Scenario odometry retry',errors,type(error).__name__,flush=True);time.sleep(.2);continue
            if start is None:start=config.get('scenario_epoch_sim_s',absolute)
            t=absolute-start
            if t-last>.15:
                wind=scenario_wind(t)
                try:
                    rpc.call('simSetWind',{'x_val':wind[1],'y_val':wind[0],'z_val':-wind[2]})
                    if not weather_enabled:rpc.call('simEnableWeather',True);weather_enabled=True
                    rpc.call('simSetWeatherParameter',7,scenario_fog(t))
                except (OSError,ValueError,RuntimeError) as error:
                    errors+=1;print('Scenario wind retry',errors,type(error).__name__,flush=True);time.sleep(.2);continue
                # Oscillating mast replaces the prototype's unbounded moving
                # column. Only lidar/camera may expose it to mission planning.
                x=3*math.sin(t*.18);enu=[x,-6,3.5]
                try:
                    moved=rpc.call('simSetObjectPose',manifest['moving_obstacle_actor'],{
                        'position':{'x_val':enu[1],'y_val':enu[0],'z_val':-enu[2]},
                        'orientation':{'x_val':0.,'y_val':0.,'z_val':0.,'w_val':1.}},True)
                    if not moved:raise RuntimeError('Moving obstacle update refused by simulator')
                except (OSError,ValueError,RuntimeError) as error:
                    errors+=1;print('Scenario obstacle retry',errors,type(error).__name__,flush=True)
                last=t
            time.sleep(.05)
