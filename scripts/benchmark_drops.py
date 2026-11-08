"""Compare RK4 release correction against a separate Gazebo rigid-body run.

Both intentionally use the same explicit quadratic-drag law. This is numerical
cross-checking, not real-world validation or proof of mission delivery accuracy.
"""
import json
import os
import signal
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
import numpy as np
from skyforge.scene import ROOT,child,model,shape
from skyforge.physics import predict_payload_offset

os.environ['GZ_PARTITION']='skyforge-drop-benchmark'
os.environ['GZ_SIM_SYSTEM_PLUGIN_PATH']='/opt/skyforge/plugins'
from gz.transport13 import Node
from gz.msgs10.pose_v_pb2 import Pose_V

root=ET.Element('sdf',version='1.9');world=child(root,'world',name='drop_bench')
physics=child(world,'physics',name='drop_physics',type='ignored')
child(physics,'max_step_size',.001);child(physics,'real_time_factor',1)
child(world,'gravity','0 0 -9.80665')
child(world,'plugin',filename='gz-sim-physics-system',name='gz::sim::systems::Physics')
child(world,'plugin',filename='gz-sim-user-commands-system',name='gz::sim::systems::UserCommands')
m,l=model(world,'ground',[0,0,-.1]);shape(l,'floor','box',[100,100,.2],[0,0,0,0,0,0],[.5,.5,.5],True)
node=Node();cases={};landings={};seen=set();lock=threading.Lock()
def callback(name,message):
    for pose in message.pose:
        if pose.name!=name:continue
        with lock:
            seen.add(name)
            if pose.position.z<=.0205 and name not in landings:
                landings[name]=[pose.position.x,pose.position.y,pose.position.z]

for height in (1.,2.2,4.):
    for wind in (0.,1.5,3.):
        prediction,duration=predict_payload_offset(height,[wind,0])
        for corrected in (False,True):
            index=len(cases);name=f'pod_{index}';target=np.array([(index%6)*3.,(index//6)*3.])
            release=target-(prediction if corrected else 0)
            m,l=model(world,name,[*release,height+.02],static=False)
            inertial=child(l,'inertial');child(inertial,'mass',.15);inertia=child(inertial,'inertia')
            for key,value in [('ixx',.15*(.10**2+.04**2)/12),('iyy',.15*(.12**2+.04**2)/12),('izz',.15*(.12**2+.10**2)/12)]:child(inertia,key,value)
            shape(l,'medical_pack','box',[.12,.10,.04],[0,0,0,0,0,0],[.95,.95,.95],True)
            p=child(m,'plugin',filename='gz-sim-pose-publisher-system',name='gz::sim::systems::PosePublisher')
            for tag,value in [('publish_model_pose','true'),('publish_link_pose','false'),('use_pose_vector_msg','true'),('update_frequency',200)]:child(p,tag,value)
            p=child(world,'plugin',filename='libSkyforgeWind.so',name='SkyforgeWind')
            for tag,value in [('model_name',name),('cd_area',.004),('constant_wind','true'),('wind_x',wind),('wind_y',0),('publish_wind','false')]:child(p,tag,value)
            node.subscribe(Pose_V,f'/model/{name}/pose',lambda message,n=name:callback(n,message))
            cases[name]={'height_m':height,'wind_m_s':wind,'corrected':corrected,'target':target.tolist(),'predicted_drift_m':prediction.tolist(),'predicted_fall_s':duration}

out=ROOT/'artifacts/drop-benchmark';out.mkdir(parents=True,exist_ok=True)
path=out/'world.sdf';ET.ElementTree(root).write(path,encoding='unicode')
with (out/'simulator.log').open('w') as log:
    process=subprocess.Popen(['gz','sim','-s','-v','1',str(path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        deadline=time.monotonic()+20
        while len(seen)<len(cases) and time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Physics server exited')
            time.sleep(.1)
        result=subprocess.run(['gz','service','-s','/world/drop_bench/control','--reqtype','gz.msgs.WorldControl','--reptype','gz.msgs.Boolean','--timeout','3000','--req','pause: false'],capture_output=True,text=True,timeout=5)
        if 'true' not in result.stdout:raise RuntimeError('Could not start drop physics: '+result.stdout)
        deadline=time.monotonic()+15
        while len(landings)<len(cases) and time.monotonic()<deadline:time.sleep(.1)
        if len(landings)!=len(cases):raise RuntimeError(f'Only {len(landings)}/{len(cases)} physical landings observed')
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGINT)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()

rows=[]
for name,case in cases.items():
    landing=landings[name];rows.append({**case,'landing':landing,'error_m':float(np.linalg.norm(np.asarray(landing[:2])-case['target']))})
report={'scope':'Gazebo/RK4 consistency under the same drag assumptions; no downwash, varying wind, release actuator, bounce or empirical calibration',
        'cases':rows,'summary':{}}
for corrected in (False,True):
    errors=[r['error_m'] for r in rows if r['corrected']==corrected]
    report['summary']['corrected' if corrected else 'uncorrected']={'n':len(errors),'mean_m':float(np.mean(errors)),'max_m':max(errors)}
(out/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['summary'],indent=2))
