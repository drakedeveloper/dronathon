"""Independent bounded classical reflex process; no models or LangGraph here."""
from collections import deque
import json
import math
import signal
import time
import zlib
import struct
import numpy as np
from gz.msgs10.stringmsg_pb2 import StringMsg
from gz.msgs10.boolean_pb2 import Boolean
from .transport import GazeboBus,rotation_xyzw
from .physics import braking_distance
from .security import Codec,ReplayGuard,PacketError,canonical,checked_vector
from .comms import load_key,envelope


def limit(vector,bound):
    norm=float(np.linalg.norm(vector))
    return vector*min(1.,bound/max(norm,1e-12))


class ReflexController:
    def __init__(self):
        self.bus=GazeboBus(camera_enabled=False);self.codec=Codec(load_key());self.guard=ReplayGuard()
        self.goal=None;self.goal_crc=None;self.running=True;self.stats_seq=0
        self.times=deque(maxlen=2000);self.overrides=0;self.bad_packets=0;self.integral=np.zeros(3)
        self.last_v=np.zeros(3);self.last_a=np.zeros(3);self.crc_hold_cycles=0
        self.bus.node.subscribe(StringMsg,"/skyforge/control",self.receive)
        self.stats=self.bus.node.advertise("/skyforge/control_stats",StringMsg)
        self.enable=self.bus.node.advertise("/X3/enable",Boolean)

    def receive(self,message):
        try:
            body=self.codec.decode(message.data.encode())
            if body["type"]!="setpoint" or not self.guard.accept(body):return
            checked_vector(body["data"]["p"],3,30)
            self.goal=body;self.goal_crc=zlib.crc32(canonical(body))
            if body["data"].get("fault_inject"):
                value=bytearray(struct.pack("d",self.goal["data"]["p"][0]));value[2]^=1
                self.goal["data"]["p"][0]=struct.unpack("d",value)[0]
        except (PacketError,KeyError,ValueError):self.bad_packets+=1

    def run(self):
        last=time.monotonic();last_publish=0.;last_sim=None
        while self.running:
            begin=time.perf_counter_ns();now=time.monotonic();dt=min(.05,max(.001,now-last));last=now
            pose=self.bus.pose;reason="OK";nearest=30.;sensor_points=[]
            desired=np.zeros(3)
            if pose is not None:
                dt=max(0.,min(.1,pose["t"]-last_sim)) if last_sim is not None else .02
                last_sim=pose["t"]
                if self.goal is None or pose["t"]*1000>self.goal["data"].get("valid_until",0):reason="STALE_AI_HOLD"
                elif zlib.crc32(canonical(self.goal))!=self.goal_crc:
                    reason="STATE_CRC_HOLD";self.crc_hold_cycles+=1
                else:
                    data=self.goal["data"];delta=np.array(data["p"])-pose["p"]
                    self.integral=np.clip(self.integral+delta*dt,-1.5,1.5)
                    desired=.85*delta+.08*self.integral
                    desired[:2]=limit(desired[:2],float(np.clip(data.get('speed_limit',.9),0,1.6)))
                    if data.get('hold'):
                        self.integral[:]=0;desired[:]=0;reason='PLANNER_HOLD'
                    desired[2]=float(np.clip(desired[2],-.65,.65))
                    for zone in data.get("zones",[]):
                        offset=np.array(zone[:2])-pose["p"][:2]
                        if np.linalg.norm(offset)<zone[2]+.6 and desired[:2]@offset>0:
                            desired[:2]=0;reason="HAZARD_BRAKE"
                    if data.get("phase")=="POSE":
                        desired[:]=0
                        if pose["p"][2]<.2:self.enable.publish(Boolean(data=False))
                    if data.get("available_wh",1)>0:
                        pass
                    else:
                        self.enable.publish(Boolean(data=False));reason="ENERGY_EXHAUSTED"
                scan=self.bus.scan
                if scan is not None and pose["p"][2]>2.5:
                    ranges=np.array(scan.ranges);angles=scan.angle_min+np.arange(len(ranges))*scan.angle_step
                    rotation=rotation_xyzw(pose["q"])
                    valid=np.isfinite(ranges)&(ranges>.7)&(ranges<14)
                    for index in np.flatnonzero(valid)[::3]:
                        ray=rotation@np.array([math.cos(angles[index]),math.sin(angles[index]),0.])
                        point=pose["p"]+ranges[index]*ray
                        if abs(point[2]-pose["p"][2])<1.5:sensor_points.append(point[:2].round(2).tolist())
                    local=rotation.T@desired;heading=math.atan2(local[1],local[0])
                    forward=np.abs(np.arctan2(np.sin(angles-heading),np.cos(angles-heading)))<.65
                    subset=ranges[forward&valid]
                    nearest=float(np.min(subset)) if len(subset) else 30.
                    stop=braking_distance(float(np.linalg.norm(pose["v"][:2])),1.5,.15,.1)+.35
                    if nearest<stop and np.linalg.norm(desired[:2])>.08:
                        desired[:2]=0;reason="LIDAR_BRAKE"
                if reason!="OK":self.overrides+=1
                acceleration=limit((desired-self.last_v)/max(dt,1e-6),1.5)
                acceleration=self.last_a+limit(acceleration-self.last_a,5.*dt)
                velocity=self.last_v+acceleration*dt
                # Do not drift indefinitely through a small desired stop command.
                if np.linalg.norm(desired)<.03 and np.linalg.norm(velocity)<.05:velocity[:]=0
                self.bus.command(velocity)
                self.last_v=velocity;self.last_a=acceleration
            self.times.append((time.perf_counter_ns()-begin)/1e6)
            if now-last_publish>.15 and pose:
                self.stats_seq+=1
                info={"t":round(pose["t"],3),"p":pose["p"].round(3).tolist(),"v":pose["v"].round(3).tolist(),
                      "reason":reason,"p95_ms":round(float(np.percentile(self.times,95)),3),"range_m":round(nearest,2),
                      "overrides":self.overrides,"bad_packets":self.bad_packets,"crc_hold_cycles":self.crc_hold_cycles,
                      "points":sensor_points[::max(1,len(sensor_points)//12)]}
                # Internal diagnostic transport is not the station radio wire.
                self.stats.publish(StringMsg(data=json.dumps(info,separators=(",",":"))));last_publish=now
            time.sleep(max(0,.02-(time.perf_counter_ns()-begin)/1e9))
        self.bus.command(np.zeros(3))


if __name__=="__main__":
    controller=ReflexController()
    signal.signal(signal.SIGINT,lambda *_:setattr(controller,"running",False))
    signal.signal(signal.SIGTERM,lambda *_:setattr(controller,"running",False))
    controller.run()
