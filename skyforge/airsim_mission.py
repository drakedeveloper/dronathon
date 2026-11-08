"""Native two-agent rescue runtime using actual AirSim images and flight state.

Consumes only the declared mission inputs; scene annotations are restricted to
the simulator/data/evaluator processes. Flight reflex is a separate process.
"""
from collections import deque
import argparse
import json
import math
import os
from pathlib import Path
import signal
import socket
import threading
import time
import uuid
import cv2
import numpy as np
from .scene import ROOT
from .airsim_backend import AirSimBackend
from .airsim_scenario import scenario_wind
from .neural_vision import NeuralVisionSystem
from .physics import Vehicle,Battery
from .planning import MissionAI
from .shield import apply_shield
from .coverage import CoverageGrid
from .explain import explain_decision
from .security import Codec
from .comms import RadioClient,load_key,envelope,clean


def atomic_json(path,data):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(clean(data),separators=(',',':'),allow_nan=False))
    return replace_live(temporary,path)


def replace_live(temporary,path):
    # Windows readers can briefly deny replacement. Dashboard publication must
    # never terminate the flight process; the next update retries fresh data.
    for attempt in range(5):
        try:os.replace(temporary,path);return True
        except PermissionError:time.sleep(.002)
    return False


class NativeMission:
    def __init__(self,config):
        self.config=config
        self.mission_inputs=json.loads((ROOT/'configs/scenes/coastal-rescue.json').read_text())['mission']
        self.vehicle=Vehicle.from_reference(ROOT/'configs/airframes/x500-research.json')
        self.battery=Battery(config.get('mission_energy_allowance_wh',self.mission_inputs['mission_energy_allowance_wh']))
        self.ai=MissionAI({'reserve_wh':1.,'survey_altitude_m':self.mission_inputs['survey_altitude_m'],'vehicle':self.vehicle})
        self.backend=AirSimBackend(port=config['api_port'],translation_enu=config.get('translation_enu',[0,0,0]))
        self.vision=NeuralVisionSystem(Path(config.get('models_dir',ROOT/'models/native')),device=config.get('vision_device','cpu'),size=config.get('vision_size',512))
        self.id='native-'+uuid.uuid4().hex[:8];self.session=uuid.uuid4().hex[:10];self.control_seq=0
        self.directory=ROOT/'artifacts/native_missions'/self.id;self.directory.mkdir(parents=True,exist_ok=True)
        self.radio=RadioClient(self.id,self.directory/'radio',port=config['radio_port'])
        self.codec=Codec(load_key(config['control_key']))
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        self.socket.bind(('127.0.0.1',config['stats_port']));self.socket.setblocking(False)
        self.destination=('127.0.0.1',config['command_port'])
        self.running=True;self.frame=None;self.batch=None;self.camera_received=0.;self.camera_errors=0
        self.vision_ms=deque(maxlen=1000);self.ai_ms=deque(maxlen=1500);self.pipeline_ms=deque(maxlen=1500)
        self.ack_frame=0;self.stats={};self.stats_received=0.;self.lock=threading.Lock()
        self.accepted_frame=0;self.acceptance_ms=deque(maxlen=1500)
        self.pose_history=deque(maxlen=100);self.pose_lock=threading.Lock()
        self.events=[];self.trace=[];self.served=set();self.supply_count=3;self.delivery_dwell={}
        self.coverage=CoverageGrid(bounds=tuple(self.mission_inputs['bounds']));self.reported=set()
        self.live=ROOT/'artifacts/live';self.live.mkdir(parents=True,exist_ok=True)
        observer=np.zeros((360,640,3),np.uint8)
        cv2.putText(observer,'Native AirSim: see the Unreal window',(24,170),cv2.FONT_HERSHEY_SIMPLEX,.65,(180,220,240),1)
        temporary=self.live/'observer.tmp.jpg';cv2.imwrite(str(temporary),observer);replace_live(temporary,self.live/'observer.jpg')
        self.log=(self.directory/'decisions.jsonl').open('w');self.fault_next=False;self.goal_revision=0;self.goal_update=None
        self.trace_log=(self.directory/'trace.jsonl').open('a',buffering=1)
        self.last_phase=None;self.last_checkpoint=-5.;self.emergency=False;self.last_coverage=-1.;self.coverage_cells=[]
        self.last_ui=-1.;self.last_camera_ui=0.

    def cameras(self):
        while self.running:
            start=time.monotonic()
            try:
                frame=self.backend.frame(pose_provider=self.poses)
                begin=time.perf_counter_ns()
                batch=self.vision.infer(frame['image'],{'frame_id':frame['frame_id'],'t_sim_ns':int(frame['t']*1e9)},
                    secondary_zoom_out=frame['pose']['p'][2]<4.)
                elapsed=(time.perf_counter_ns()-begin)/1e6
                with self.lock:self.frame=frame;self.batch=batch;self.camera_received=time.monotonic();self.vision_ms.append(elapsed)
            except (OSError,ValueError,RuntimeError):self.camera_errors+=1
            time.sleep(max(0,.06-(time.monotonic()-start)))

    def emit(self,kind,data,t):
        self.events.append({'type':kind,**clean(data)});self.radio.event(kind,data,t)

    def poses(self):
        with self.pose_lock:return list(self.pose_history)

    def receive_stats(self):
        while True:
            try:packet,_=self.socket.recvfrom(16384)
            except BlockingIOError:break
            except ConnectionResetError:break
            try:
                data=json.loads(packet);checked=np.asarray([*data['p'],*data['v'],*data['q'],data['t']],float)
                if not np.all(np.isfinite(checked)):continue
                self.stats=data;self.stats_received=time.monotonic()
                with self.pose_lock:
                    self.pose_history.append({'t':data['t'],'t_ns':int(data['t']*1e9),
                        'p':np.asarray(data['p'],float),'v':np.asarray(data['v'],float),'q':np.asarray(data['q'],float)})
                identity=data.get('completed_frame_ns',0);latency=data.get('completed_latency_ms')
                if identity and identity!=self.ack_frame and isinstance(latency,(float,int)) and 0<=latency<10000:
                    self.ack_frame=identity;self.pipeline_ms.append(latency)
                identity=data.get('accepted_frame_ns',0);latency=data.get('accepted_latency_ms')
                if identity and identity!=self.accepted_frame and isinstance(latency,(float,int)) and 0<=latency<10000:
                    self.accepted_frame=identity;self.acceptance_ms.append(latency)
            except (ValueError,KeyError,TypeError):continue

    def run(self):
        camera_thread=threading.Thread(target=self.cameras,daemon=True);camera_thread.start()
        start_sim=None;last_sim=None;last_ai_frame=None;decision=None;snapshot_seq=0
        try:
            wall_start=time.monotonic()
            while self.running:
                begin=time.monotonic();self.receive_stats()
                if not self.stats:
                    if begin-wall_start>30:raise RuntimeError('Native reflex odometry unavailable')
                    time.sleep(.03);continue
                absolute=self.stats['t']
                if start_sim is None:
                    start_sim=absolute;last_sim=absolute
                    self.emit('mission_started',{'backend':'native_airsim','vision':self.vision.device,
                        'airframe':'x500-research','mass_kg':self.vehicle.mass_kg,
                        'initial_energy_wh':self.battery.remaining_wh},0)
                t=absolute-start_sim;dt=max(0,absolute-last_sim);last_sim=absolute
                pos=np.asarray(self.stats['p']);velocity=np.asarray(self.stats['v'])
                weather_t=absolute-self.config.get('scenario_epoch_sim_s',start_sim)
                wind=np.asarray(scenario_wind(weather_t))
                power=self.vehicle.power_w(float(np.linalg.norm(velocity-wind)),float(velocity[2])) if self.stats.get('armed') else self.vehicle.electronics_power_w
                self.battery.consume(power,dt)
                for command in self.radio.pop_commands():
                    if command['type']=='goal_update':
                        revision=command['data'].get('revision',0);goal=command['data']['position']
                        if revision>self.goal_revision and -14<=goal[0]<=14 and -11<=goal[1]<=11 and .5<=goal[2]<=8:
                            self.goal_revision=revision;self.goal_update={'position':goal};self.emit('goal_update_accepted',{'revision':revision,'position':goal},t)
                    elif command['type']=='state_bitflip':self.fault_next=True;self.emit('state_fault_injected',{},t)
                with self.lock:
                    frame=self.frame;batch=self.batch;camera_received=self.camera_received
                    vision_times=list(self.vision_ms)
                if not camera_thread.is_alive():raise RuntimeError('Camera worker failed; triggering landing recovery')
                if frame is None and begin-wall_start>25:raise RuntimeError('No usable camera frame; triggering landing recovery')
                if frame and frame['frame_id']!=last_ai_frame:
                    self.coverage.update(frame)
                    observed=list(self.mission_inputs['known_obstacles'])
                    observed += [{'x':p[0],'y':p[1],'radius':.10,'kind':'lidar'} for p in self.stats.get('points',[]) if math.dist(p,pos[:2])<7]
                    snapshot_seq+=1
                    snapshot={'position_enu_m':pos.tolist(),'base_enu_m':self.config['base_enu_m'],
                        'wind_enu_mps':wind.tolist(),'battery_wh':self.battery.remaining_wh,'events':self.events[-30:],
                        'supply_count':self.supply_count,'frame':frame,'detections':batch,'snapshot_seq':snapshot_seq,
                        'goal_revision':self.goal_revision,'goal_update':self.goal_update,'map_revision':snapshot_seq,
                        'obstacle_circles':observed,'urgency_observations':self.mission_inputs['distress_observations'],'t_sim_s':t}
                    ai_start=time.perf_counter_ns();decision=self.ai.step(snapshot)
                    decision=apply_shield(snapshot,decision,self.ai.perception.tracks)
                    self.ai_ms.append((time.perf_counter_ns()-ai_start)/1e6);last_ai_frame=frame['frame_id'];self.events=[]
                    if decision['phase']!=self.last_phase:
                        self.emit('phase_changed',{'phase':decision['phase'],'reason':decision['decision_code']},t);self.last_phase=decision['phase']
                    self.log.write(json.dumps(clean({'t':t,'decision':decision}),separators=(',',':'))+'\n');self.log.flush()
                    overlay=frame['image'].copy()
                    for detection in batch['detections']:
                        x0,y0,x1,y1=map(int,detection['bbox_xyxy']);cv2.rectangle(overlay,(x0,y0),(x1,y1),(60,210,255),2)
                        cv2.putText(overlay,detection['class'],(x0,max(12,y0-4)),cv2.FONT_HERSHEY_SIMPLEX,.35,(40,245,255),1)
                    if begin-self.last_camera_ui>=.2:
                        temporary=self.live/'camera.tmp.jpg';cv2.imwrite(str(temporary),overlay,[cv2.IMWRITE_JPEG_QUALITY,82]);replace_live(temporary,self.live/'camera.jpg')
                        self.last_camera_ui=begin
                if decision:
                    base=np.asarray(self.config['base_enu_m']);near_base=np.linalg.norm(pos[:2]-base[:2])<.6
                    if self.battery.remaining_wh<.8 and not self.emergency:
                        self.emergency=True;self.emit('emergency_landing',{'reason':'ENERGY_CRITICAL'},t)
                    # Native pawn ground height differs from the small Gazebo
                    # model. Require low height AND low speed, not just a phase.
                    low=abs(pos[2]-self.config['home_body_z'])<.18 and np.linalg.norm(velocity)<.18
                    if self.emergency:
                        route=[pos.tolist(),[float(pos[0]),float(pos[1]),.03]]
                        decision={**decision,'phase':'POSE' if low else 'RETOUR_BASE','waypoints_enu_m':route,
                                  'decision_code':'EMERGENCY_LOW_ENERGY_LAND','request_delivery':None}
                    elif decision['phase']=='RETOUR_BASE' and near_base and low:
                        decision={**decision,'phase':'POSE','decision_code':'LANDED','request_delivery':None}
                    route=decision['waypoints_enu_m'];target=np.asarray(route[-1],float)
                    for waypoint in route[1:]:
                        if np.linalg.norm(np.asarray(waypoint)-pos)>.4:target=np.asarray(waypoint);break
                    stale=(begin-camera_received>.4 or begin-self.stats_received>.25)
                    if stale and decision['phase'] not in ('RETOUR_BASE','POSE'):target=pos.copy()
                    tracks=list(self.ai.perception.tracks.values())
                    zones=[[*track['position'][:2],1.8] for track in tracks if track['class'] in ('mine','weapon','hostile_unit') or track.get('classification_uncertain')]
                    usable=max(0.,pos[2]*math.tan(.6)*.75-2.35-.55)
                    speed=min(.9,max(0.,math.sqrt(.45**2+3*usable)-.45))
                    data={'p':target.round(3).tolist(),'phase':decision['phase'],'valid_until':int((absolute+.65)*1000),
                        'zones':zones[:8],'available_wh':round(self.battery.remaining_wh,3),'hold':len(route)<=1 or (stale and decision['phase'] not in ('RETOUR_BASE','POSE')),
                        'speed_limit':round(speed,3),'frame_request_wall_ns':frame['request_wall_ns']}
                    if self.fault_next:data['fault_inject']=True;self.fault_next=False
                    self.control_seq+=1
                    packet=self.codec.encode(envelope(self.id,self.session,'command',self.control_seq,absolute,'setpoint',data))
                    self.socket.sendto(packet,self.destination)
                    request=decision.get('request_delivery')
                    if request and request['request_id'] not in self.served:
                        key=request['request_id']
                        if np.linalg.norm(velocity)<.2:
                            self.delivery_dwell.setdefault(key,t)
                            if t-self.delivery_dwell[key]>1:
                                self.served.add(key);self.supply_count-=1
                                self.emit('delivery_completed',{'target_track_id':request['target_track_id'],'mode':'virtual_hover_delivery'},t)
                        else:self.delivery_dwell.pop(key,None)
                    for track in tracks:
                        if track['id'] not in self.reported and track['seen_count']>=2:
                            self.emit('object_detected',{'id':track['id'],'class':track['class'],'p':np.round(track['position'],2).tolist()},t);self.reported.add(track['id'])
                    if t-self.last_coverage>.5:self.coverage_cells=self.coverage.cells();self.last_coverage=t
                    # UI/radio diagnostics run at 5 Hz; flight and trace retain 50 Hz.
                    if begin-self.last_ui>=.2 or decision['phase']=='POSE':
                        detail=decision['decision_details']
                        status={'t':round(t,2),'phase':decision['phase'],'p':pos.round(3).tolist(),'energy':round(self.battery.remaining_wh,3),
                            'return_threshold':detail.get('return_threshold_wh'),'served':len(self.served),'pending_events':len(self.radio.events),
                            'goal_revision':self.goal_revision}
                        self.radio.publish_status(status,t)
                        if t-self.last_checkpoint>5:
                            self.emit('mission_checkpoint',{'p':status['p'],'energy':status['energy'],'phase':status['phase'],'served':status['served']},t);self.last_checkpoint=t
                        diagnostic={**status,'mission_id':self.id,'backend':'native_airsim','decision':decision['decision_code'],
                            'explanation':explain_decision(decision),'wind_speed':float(np.linalg.norm(wind)),
                            'ai_p95_ms':float(np.percentile(self.ai_ms,95)) if self.ai_ms else 0.,
                            'vision_p95_ms':float(np.percentile(vision_times,95)) if vision_times else 0.,
                            'pipeline_p95_ms':float(np.percentile(self.pipeline_ms,95)) if self.pipeline_ms else None,
                            'pipeline_scope':'camera request to completed velocity RPC; conservative completion upper bound',
                            'command_acceptance_p95_ms':float(np.percentile(self.acceptance_ms,95)) if self.acceptance_ms else None,
                            'command_acceptance_scope':'camera request to authenticated first receipt in reflex mailbox; excludes velocity RPC completion',
                            'control':self.stats,'security':dict(self.radio.counters),'route':route,'obstacles':observed,
                            'coverage':self.coverage.summary(),'coverage_cells':self.coverage_cells,'camera_errors':self.camera_errors,
                            'tracks':[{**track,'served':track['id'] in self.ai.planner.served} for track in tracks],
                            'airframe_mass_kg':self.vehicle.mass_kg,'vision_device':self.vision.device,'model_domain':'rendered_development'}
                        atomic_json(self.live/'onboard.json',diagnostic)
                        self.last_ui=begin
                    sample={'t':t,'absolute_t':absolute,'p':pos.tolist(),'energy':self.battery.remaining_wh,
                            'phase':decision['phase'],'collision':self.stats.get('collision',{})}
                    self.trace.append(sample);self.trace_log.write(json.dumps(sample,separators=(',',':'))+'\n')
                    if decision['phase']=='POSE':
                        self.emit('mission_landed',{'deliveries':len(self.served),'at_base':near_base and not self.emergency},t)
                        time.sleep(1);break
                if t>self.config.get('max_mission_seconds',360):self.emit('mission_timeout',{},t);break
                time.sleep(max(0,.02-(time.monotonic()-begin)))
        finally:
            self.running=False;camera_thread.join(timeout=4)
            (self.directory/'trace.json').write_text(json.dumps(clean(self.trace)))
            (self.directory/'observed-ground.json').write_text(json.dumps({**self.coverage.summary(),'cells':self.coverage.cells()}))
            self.trace_log.close();self.log.close();self.backend.close();self.radio.close();self.socket.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config',type=Path);args=parser.parse_args()
    mission=NativeMission(json.loads(args.config.read_text()))
    signal.signal(signal.SIGINT,lambda *_:setattr(mission,'running',False))
    signal.signal(signal.SIGTERM,lambda *_:setattr(mission,'running',False))
    mission.run()
