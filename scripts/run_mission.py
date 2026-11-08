"""Launch a fresh isolated mission, physical controller and optional Gazebo GUI."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import time
from skyforge.scene import ROOT,create_world

parser=argparse.ArgumentParser();parser.add_argument("--gui",action="store_true");args=parser.parse_args()
os.environ["GZ_PARTITION"]="skyforge-mission"
os.environ["GZ_SIM_SYSTEM_PLUGIN_PATH"]="/opt/skyforge/plugins:"+os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH","")
os.environ["GZ_SIM_RESOURCE_PATH"]=str(ROOT/"sim/models")+":"+os.environ.get("GZ_SIM_RESOURCE_PATH","")
path,_=create_world();out=ROOT/"artifacts";processes=[];handles=[]
out.mkdir(parents=True,exist_ok=True)


def launch(command,name):
    handle=(out/f"mission-{name}.log").open("w");handles.append(handle)
    p=subprocess.Popen(command,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True);processes.append(p);return p


try:
    simulator=launch(["gz","sim","-s","-r","-v","2",str(path)],"simulator")
    time.sleep(3)
    if simulator.poll() is not None:raise RuntimeError('Simulator failed during startup; inspect artifacts/mission-simulator.log')
    gui=launch(["gz","sim","-g"],"gui") if args.gui else None
    controller=launch(["python","-m","skyforge.controller"],"controller")
    runtime=launch(["python","-m","skyforge.runtime"],"runtime")
    print("Mission running; local dashboard http://localhost:8766",flush=True)
    while runtime.poll() is None:
        if simulator.poll() is not None:raise RuntimeError('Simulator exited; mission stopped')
        if controller.poll() is not None:raise RuntimeError('Safety controller exited; mission stopped')
        time.sleep(.25)
    if runtime.returncode:raise RuntimeError(f"Mission runtime failed ({runtime.returncode}); inspect artifacts/mission-runtime.log")
    if gui and gui.poll() is None:
        print('Mission finished. Gazebo viewer remains open; close its window or press Ctrl+C to stop.',flush=True)
        while gui.poll() is None:
            if simulator.poll() is not None:raise RuntimeError('Simulator exited while viewer was open')
            time.sleep(.25)
finally:
    for p in reversed(processes):
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGINT)
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=5)
    for h in handles:h.close()
