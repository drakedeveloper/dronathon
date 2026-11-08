"""Independent native AirSim reflex process. No models, LangGraph or LLMs."""
from collections import deque
import argparse
import json
import math
from pathlib import Path
import signal
import socket
import struct
import threading
import time
import zlib
import numpy as np
from .airsim_backend import AirSimBackend
from .comms import load_key
from .physics import braking_distance
from .security import Codec,ReplayGuard,PacketError,canonical,checked_vector


def limit(vector,bound):
    length=float(np.linalg.norm(vector))
    return vector*min(1.,bound/max(1e-12,length))


class NativeMailbox:
    def __init__(self,key):
        self.codec=Codec(key);self.guard=ReplayGuard();self.goal=None;self.crc=None
        self.received_wall=0.;self.rejected=0
    def receive(self,packet):
        try:
            body=self.codec.decode(packet)
            if body['type']!='setpoint' or not self.guard.accept(body):return False
            checked_vector(body['data']['p'],3,1000)
            for zone in body['data'].get('zones',[]):checked_vector(zone,3,1000)
            self.goal=body;self.crc=zlib.crc32(canonical(body));self.received_wall=time.monotonic()
            if body['data'].get('fault_inject'):
                changed=bytearray(struct.pack('d',body['data']['p'][0]));changed[2]^=1
                body['data']['p'][0]=struct.unpack('d',changed)[0]
            return True
        except (PacketError,ValueError,KeyError,TypeError):self.rejected+=1;return False
    def reason(self,sim_time):
        if self.goal is None or time.monotonic()-self.received_wall>.65:return 'STALE_AI_HOLD'
        if zlib.crc32(canonical(self.goal))!=self.crc:return 'STATE_CRC_HOLD'
        if sim_time*1000>self.goal['data'].get('valid_until',0):return 'STALE_AI_HOLD'
        return 'OK'


class NativeReflex:
    def __init__(self,config):
        self.config=config;self.backend=AirSimBackend(port=config['api_port'],translation_enu=config.get('translation_enu',[0,0,0]))
        self.mailbox=NativeMailbox(load_key(config['control_key']))
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        self.socket.bind(('127.0.0.1',config['command_port']));self.socket.setblocking(False)
        self.stats_destination=('127.0.0.1',config['stats_port']);self.running=True
        self.pose=None;self.pose_received=0.;self.points=np.empty((0,3));self.pose_errors=0
        self.output=np.zeros(3);self.armed=False;self.lock=threading.Lock()
        self.stop_reason=None;self.lidar_received=0.;self.lidar_errors=0
        self.output_frame_ns=0;self.completed_frame_ns=0;self.completed_latency_ms=None
        self.times=deque(maxlen=2000);self.crc_holds=0;self.override_cycles=0;self.last_frame=0

    def sense(self):
        last_scan=0.
        while self.running:
            start=time.monotonic()
            try:
                pose=self.backend.state();self.pose=pose;self.pose_received=time.monotonic()
                if start-last_scan>.15:
                    try:
                        points=self.backend.lidar_points()
                        distance=np.linalg.norm(points[:,:2]-pose['p'][:2],axis=1)
                        valid=np.all(np.isfinite(points),axis=1)&(distance>.7)&(distance<20)&(abs(points[:,2]-pose['p'][2])<1.5)
                        self.points=points[valid];last_scan=start;self.lidar_received=time.monotonic()
                    except (OSError,ValueError,RuntimeError):self.points=np.empty((0,3));self.lidar_errors+=1
            except (OSError,ValueError,RuntimeError):self.pose_errors+=1
            time.sleep(max(0,.02-(time.monotonic()-start)))

    def send_velocity(self):
        while self.running:
            start=time.monotonic()
            if self.armed:
                try:
                    with self.lock:velocity=self.output.copy();frame_ns=self.output_frame_ns
                    self.backend.velocity(velocity,duration=.02)
                    if frame_ns and frame_ns!=self.completed_frame_ns:
                        self.completed_frame_ns=frame_ns
                        self.completed_latency_ms=max(0.,(time.monotonic_ns()-frame_ns)/1e6)
                except (OSError,ValueError,RuntimeError):self.pose_errors+=1
            time.sleep(max(0,.02-(time.monotonic()-start)))

    def run(self):
        workers=[threading.Thread(target=self.sense,daemon=True),threading.Thread(target=self.send_velocity,daemon=True)]
        for worker in workers:worker.start()
        integral=np.zeros(3);last_v=np.zeros(3);last_a=np.zeros(3);last_t=None;last_publish=0.
        try:
            while self.running:
                begin=time.perf_counter_ns();now=time.monotonic()
                while True:
                    try:packet,_=self.socket.recvfrom(2048)
                    except BlockingIOError:break
                    except ConnectionResetError:break  # Windows UDP ICMP before receiver binds
                    self.mailbox.receive(packet)
                pose=self.pose;reason='WAITING_ODOMETRY';desired=np.zeros(3);nearest=30.;dt=0.
                if pose:
                    dt=max(0,min(.1,pose['t']-last_t)) if last_t is not None else .02;last_t=pose['t']
                    reason=self.mailbox.reason(pose['t'])
                    if now-self.pose_received>.25:reason='STALE_ODOMETRY_HOLD'
                    if now-self.lidar_received>.6:reason='STALE_LIDAR_HOLD'
                    if self.stop_reason:reason=self.stop_reason
                    if reason=='STATE_CRC_HOLD':self.crc_holds+=1
                    if reason=='OK':
                        data=self.mailbox.goal['data']
                        if not self.armed:
                            self.backend.enable_control();self.armed=True
                        delta=np.asarray(data['p'])-pose['p'];integral=np.clip(integral+delta*dt,-1.5,1.5)
                        desired=.85*delta+.08*integral
                        desired[:2]=limit(desired[:2],float(np.clip(data.get('speed_limit',.9),0,1.2)))
                        desired[2]=float(np.clip(desired[2],-.65,.65))
                        if data.get('hold'):desired[:]=0;integral[:]=0;reason='PLANNER_HOLD'
                        for zone in data.get('zones',[]):
                            offset=np.asarray(zone[:2])-pose['p'][:2]
                            if np.linalg.norm(offset)<zone[2]+.6 and desired[:2]@offset>0:
                                desired[:2]=0;reason='HAZARD_BRAKE'
                        if len(self.points) and np.linalg.norm(desired[:2])>.05:
                            relative=self.points[:,:2]-pose['p'][:2];distance=np.linalg.norm(relative,axis=1)
                            forward=(relative@desired[:2])/np.maximum(1e-9,distance*np.linalg.norm(desired[:2]))>.75
                            if np.any(forward):nearest=float(distance[forward].min())
                            stop=braking_distance(float(np.linalg.norm(pose['v'][:2])),1.5,.3,.1)+.35
                            if nearest<stop:desired[:2]=0;reason='LIDAR_BRAKE'
                        home=np.asarray(self.config['base_enu_m'])
                        at_ground=(abs(pose['p'][2]-self.config['home_body_z'])<.18 and np.linalg.norm(pose['v'])<.18)
                        can_disarm=data['phase']=='POSE' and at_ground
                        if can_disarm or data.get('available_wh',1)<=0:
                            self.armed=False;self.backend.control_enabled=False
                            self.backend.commands.call('armDisarm',False,self.backend.vehicle)
                            desired[:]=0;reason='LANDED' if can_disarm else 'ENERGY_EXHAUSTED'
                            self.stop_reason=reason
                    if reason!='OK':self.override_cycles+=1
                    acceleration=limit((desired-last_v)/max(1e-6,dt),1.5)
                    acceleration=last_a+limit(acceleration-last_a,5*dt)
                    velocity=limit(last_v+acceleration*dt,1.6)
                    if np.linalg.norm(desired)<.03 and np.linalg.norm(velocity)<.05:velocity[:]=0
                    with self.lock:
                        self.output=velocity
                        self.output_frame_ns=self.mailbox.goal['data'].get('frame_request_wall_ns',0) if self.mailbox.goal else 0
                    last_v=velocity;last_a=acceleration
                self.times.append((time.perf_counter_ns()-begin)/1e6)
                if pose and now-last_publish>.02:
                    info={'t':pose['t'],'p':pose['p'].tolist(),'v':pose['v'].tolist(),'q':pose['q'].tolist(),
                          'reason':reason,'p95_ms':float(np.percentile(self.times,95)),
                          'range_m':nearest,'points':self.points[::max(1,len(self.points)//24),:2].round(2).tolist(),
                          'crc_hold_cycles':self.crc_holds,'overrides':self.override_cycles,
                          'pose_errors':self.pose_errors,'lidar_errors':self.lidar_errors,
                          'completed_frame_ns':self.completed_frame_ns,'completed_latency_ms':self.completed_latency_ms,
                          'bad_packets':self.mailbox.rejected,'armed':self.armed}
                    self.socket.sendto(json.dumps(info,separators=(',',':'),allow_nan=False).encode(),self.stats_destination)
                    last_publish=now
                time.sleep(max(0,.02-(time.perf_counter_ns()-begin)/1e9))
        finally:
            self.running=False
            with self.lock:self.output[:]=0
            for worker in workers:worker.join(timeout=3)
            self.backend.close();self.socket.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config',type=Path);args=parser.parse_args()
    controller=NativeReflex(json.loads(args.config.read_text()))
    signal.signal(signal.SIGINT,lambda *_:setattr(controller,'running',False))
    signal.signal(signal.SIGTERM,lambda *_:setattr(controller,'running',False))
    controller.run()
