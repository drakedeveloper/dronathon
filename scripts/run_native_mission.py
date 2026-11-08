"""Start the native station, weather, independent reflex and rescue agents.

Requires the custom FastPhysics scene already running. Calibration reads the
known launch position only; no entity annotations enter the mission process.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import numpy as np
from skyforge.airsim_backend import AirSimBackend
from skyforge.comms import load_key
from skyforge.scene import ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    parser.add_argument('--models',type=Path,default=ROOT/'models')
    args=parser.parse_args()
    backend=AirSimBackend(port=41461)
    settings=json.loads(backend.navigation.call('getSettingsString'))
    if settings.get('SkyforgeScenario')!='coastal-rescue' or settings.get('PhysicsEngineName')!='FastPhysicsEngine':
        raise RuntimeError('Launch the custom physical coastal-rescue scene first')
    backend.commands.call('simRunConsoleCommand','t.MaxFPS 60')
    first=backend.state();time.sleep(.5);second=backend.state()
    if np.linalg.norm(second['v'])>.15 or np.linalg.norm(second['p']-first['p'])>.08:
        raise RuntimeError('Launch calibration requires a stationary grounded drone')
    if second['p'][2]<-1:raise RuntimeError('Drone below launch ground; inspect collision setup')
    if np.linalg.norm(second['p'][:2])>.5:raise RuntimeError('Drone must be on its declared launch pad before calibration')
    inputs=json.loads((ROOT/'configs/scenes/coastal-rescue.json').read_text())['mission']
    spawn=settings['Vehicles']['SKYFORGE']
    translation=[spawn['Y'],spawn['X'],-spawn['Z']]
    ground_body_z=float(second['p'][2]+translation[2])
    base=[*inputs['base_enu_m'][:2],ground_body_z]
    backend.close()
    folder=ROOT/'artifacts/native';folder.mkdir(parents=True,exist_ok=True)
    control=ROOT/'runtime/secrets/native-control.key';load_key(control)
    radio=ROOT/'runtime/secrets/native-radio.key';load_key(radio)
    config={'api_port':41461,'translation_enu':translation,'base_enu_m':base,
            'home_body_z':base[2],'control_key':str(control),'command_port':42101,
            'stats_port':42102,'radio_port':8767,'vision_device':args.device,
            'models_dir':str(args.models.resolve()),
            'scene_manifest':str(ROOT/'runtime/unreal/SKYFORGE/scene-manifest.json'),
            'max_mission_seconds':360}
    config_path=folder/'config.json';config_path.write_text(json.dumps(config,indent=2))
    env={**os.environ,'SKYFORGE_HTTP_PORT':'8768','SKYFORGE_RADIO_PORT':'8767',
         'SKYFORGE_RADIO_KEY':str(radio),'PYTHONUNBUFFERED':'1'}
    children=[];handles=[];running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    def launch(name,arguments):
        handle=(folder/(name+'.log')).open('w');handles.append(handle)
        child=subprocess.Popen([sys.executable,*arguments],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT)
        children.append(child);return child
    try:
        launch('station',['-m','station.server'])
        launch('scenario',['-m','skyforge.airsim_scenario',str(config_path)])
        launch('reflex',['-m','skyforge.airsim_controller',str(config_path)])
        mission=launch('mission',['-m','skyforge.airsim_mission',str(config_path)])
        print('Native mission running. Station http://127.0.0.1:8768',flush=True)
        while running and mission.poll() is None:
            failed=[child.pid for child in children[:-1] if child.poll() is not None]
            if failed:raise RuntimeError(f'Native child exited: {failed}; inspect {folder}')
            time.sleep(.25)
        if mission.poll() not in (None,0):raise RuntimeError('Native mission failed; inspect mission.log')
    finally:
        # Owned services only; never terminate the visible Unreal simulator.
        for child in reversed(children):
            if child.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else:child.terminate()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        # An aborted agent must not leave the simulator unattended in flight.
        # Land vertically at the current position; never disarm in the air.
        recovery=AirSimBackend(port=41461,translation_enu=translation)
        try:
            if recovery.commands.call('isApiControlEnabled','SKYFORGE'):
                for _ in range(180):
                    pose=recovery.state()
                    if abs(pose['p'][2]-base[2])<.18 and np.linalg.norm(pose['v'])<.18:
                        recovery.commands.call('armDisarm',False,'SKYFORGE');break
                    recovery.commands.call('moveByVelocity',0.,0.,.5,.2,0,
                        {'is_rate':True,'yaw_or_rate':0.},'SKYFORGE')
                else:recovery.commands.call('hover','SKYFORGE')
        except (OSError,RuntimeError,ValueError) as error:
            print(f'Simulator landing recovery unavailable: {error}',flush=True)
        finally:recovery.close()
        for handle in handles:handle.close()


if __name__=='__main__':main()
