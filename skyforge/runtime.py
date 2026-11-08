"""Mission integration. Classical motor control runs in a separate process."""
from collections import deque
import json
import math
import os
from pathlib import Path
import signal
import time
import uuid
import cv2
import numpy as np
from gz.msgs10.stringmsg_pb2 import StringMsg
from gz.msgs10.image_pb2 import Image
from .scene import ROOT
from .transport import GazeboBus
from .vision import VisionSystem
from .planning import MissionAI,Circle,segment_clear
from .physics import Vehicle,Battery
from .security import Codec
from .comms import RadioClient,envelope,load_key,clean


def atomic_json(path,data):
    temporary=path.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean(data),separators=(",",":"),allow_nan=False));os.replace(temporary,path)


class Runtime:
    def __init__(self):
        self.bus=GazeboBus()
        self.vision_backend=os.environ.get('SKYFORGE_VISION','forest')
        if self.vision_backend=='onnx':
            from .neural_vision import NeuralVisionSystem
            self.vision=NeuralVisionSystem(ROOT/'models')
        else:self.vision=VisionSystem(ROOT/"models")
        self.ai=MissionAI({"reserve_wh":1.0})
        self.vehicle=Vehicle();self.battery=Battery(15.)
        self.id="mission-"+uuid.uuid4().hex[:8];self.session=uuid.uuid4().hex[:10]
        self.radio=RadioClient(self.id,ROOT/"artifacts/journal");self.codec=Codec(load_key())
        self.control_pub=self.bus.node.advertise("/skyforge/control",StringMsg)
        self.bus.node.subscribe(StringMsg,"/skyforge/control_stats",self.on_control)
        self.bus.node.subscribe(Image,"/skyforge/observer",self.on_observer)
        self.running=True;self.control={};self.seq=0;self.goal_revision=0;self.goal_update=None
        self.events=[];self.supply_count=3;self.delivered=set();self.delivery_dwell={}
        self.ai_times=deque(maxlen=1500);self.pipeline_times=deque(maxlen=1500)
        self.out=ROOT/"artifacts/live";self.out.mkdir(parents=True,exist_ok=True)
        self.log_dir=ROOT/"artifacts/missions"/self.id;self.log_dir.mkdir(parents=True,exist_ok=True)
        self.log=(self.log_dir/"decisions.jsonl").open("w")
        self.trace=[];self.last_phase=None;self.fault_next=False;self.last_observer_write=0.
        self.emergency=False
        self.reported_tracks={};self.last_checkpoint=-5.
        self.map_obstacles=[{"x":-2.,"y":-2.,"radius":2.15,"kind":"known_static"},
                            {"x":5.,"y":4.,"radius":1.80,"kind":"known_static"}]
        # Explicitly modeled distress-beacon metadata: urgency is not diagnosed
        # from appearance. Vision confirmation is required before rescue.
        self.beacons=[{"position":[-7,-5,0],"urgency":1,"source":"simulated_distress_beacon"},
                      {"position":[9,-3,0],"urgency":3,"source":"simulated_distress_beacon"},
                      {"position":[3,9,0],"urgency":2,"source":"simulated_distress_beacon"}]

    def on_control(self,message):
        try:self.control=json.loads(message.data)
        except (ValueError,TypeError):pass

    def on_observer(self,message):
        if time.monotonic()-self.last_observer_write<.2:return
        try:
            rgb=np.frombuffer(message.data,np.uint8).reshape(message.height,message.step)[:,:message.width*3].reshape(message.height,message.width,3)
            image=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
            temp=self.out/"observer.tmp.jpg";cv2.imwrite(str(temp),image,[cv2.IMWRITE_JPEG_QUALITY,82]);os.replace(temp,self.out/"observer.jpg")
            self.last_observer_write=time.monotonic()
        except (ValueError,OSError):pass

    def emit(self,kind,data,t):
        event={"type":kind,**clean(data)};self.events.append(event)
        self.radio.event(kind,data,t)

    def run(self):
        deadline=time.monotonic()+40
        while self.bus.pose is None and time.monotonic()<deadline:time.sleep(.1)
        if self.bus.pose is None:raise RuntimeError("No drone odometry")
        start_sim=self.bus.pose["t"];last_sim=start_sim;last_ai_wall=0.;last_frame=-1;batch=None;decision=None
        self.emit("mission_started",{"vision":self.vision_backend,"control":"physical rotor model"},0)
        while self.running:
            begin=time.monotonic();pose=self.bus.pose
            if pose is None:time.sleep(.02);continue
            absolute=pose["t"];t=absolute-start_sim;dt=max(0,absolute-last_sim);last_sim=absolute
            power=self.vehicle.power_w(float(np.linalg.norm(pose["v"]-self.bus.wind)),float(pose["v"][2]))
            if dt>.25:power=max(power,self.vehicle.power_w(0)*1.3)
            self.battery.consume(power,dt)
            self.bus.move_obstacle([.65*math.cos(t*.18),0,0])
            for command in self.radio.pop_commands():
                if command["type"]=="goal_update":
                    rev=command["data"].get("revision",0);position=command["data"]["position"]
                    if rev>self.goal_revision and -14<=position[0]<=14 and -11<=position[1]<=11 and .5<=position[2]<=8:
                        self.goal_revision=rev;self.goal_update={"position":position}
                        self.emit("goal_update_accepted",{"revision":rev,"position":position},t)
                elif command["type"]=="state_bitflip":self.fault_next=True;self.emit("state_fault_injected",{},t)
            frame=self.bus.frame()
            if frame and begin-last_ai_wall>=.15:
                if frame["frame_id"]!=last_frame:
                    batch=self.vision.infer(frame["image"],{"frame_id":frame["frame_id"],"t_sim_ns":int(frame["t"]*1e9)})
                    last_frame=frame["frame_id"]
                self.seq+=1
                observed=list(self.map_obstacles)
                for point in self.control.get("points",[]):
                    # Observed lidar points, not the world target manifest.
                    if np.linalg.norm(np.array(point)-pose["p"][:2])<7:
                        observed.append({"x":point[0],"y":point[1],"radius":.10,"kind":"lidar"})
                snapshot={"position_enu_m":pose["p"].tolist(),"base_enu_m":[-12,-9,.055],"wind_enu_mps":self.bus.wind.tolist(),'t_sim_s':t,
                          "battery_wh":self.battery.remaining_wh,"events":self.events[-20:],"supply_count":self.supply_count,
                          "frame":frame,"detections":batch,"snapshot_seq":self.seq,"goal_revision":self.goal_revision,
                          "goal_update":self.goal_update,"map_revision":self.seq,"obstacle_circles":observed,"urgency_observations":self.beacons}
                ai_start=time.perf_counter_ns();decision=self.ai.step(snapshot);self.ai_times.append((time.perf_counter_ns()-ai_start)/1e6)
                self.events=[];last_ai_wall=begin
                if decision["phase"]!=self.last_phase:
                    self.emit("phase_changed",{"phase":decision["phase"],"reason":decision["decision_code"]},t);self.last_phase=decision["phase"]
                self.log.write(json.dumps(clean({"t":t,"decision":decision}),separators=(",",":"))+"\n");self.log.flush()
                overlay=frame["image"].copy()
                for detection in batch["detections"] if batch else []:
                    x0,y0,x1,y1=map(int,detection["bbox_xyxy"])
                    cv2.rectangle(overlay,(x0,y0),(x1,y1),(60,210,255),2)
                    cv2.putText(overlay,detection["class"],(x0,max(12,y0-4)),cv2.FONT_HERSHEY_SIMPLEX,.35,(40,245,255),1)
                temp=self.out/"camera.tmp.jpg";cv2.imwrite(str(temp),overlay,[cv2.IMWRITE_JPEG_QUALITY,85]);os.replace(temp,self.out/"camera.jpg")
            if decision:
                if self.battery.remaining_wh<.8 and np.linalg.norm(pose["p"][:2]-[-12,-9])>1.:
                    if not self.emergency:self.emit("emergency_landing",{"reason":"RETURN_UNAVAILABLE_ENERGY_CRITICAL"},t)
                    self.emergency=True
                if self.emergency:
                    decision["waypoints_enu_m"]=[pose["p"].tolist(),[float(pose["p"][0]),float(pose["p"][1]),.08]]
                    decision["phase"]="POSE" if pose["p"][2]<.17 else "RETOUR_BASE"
                    decision["decision_code"]="EMERGENCY_LOW_ENERGY_LAND"
                route=decision["waypoints_enu_m"];setpoint=np.array(route[-1])
                for waypoint in route[1:]:
                    if np.linalg.norm(np.array(waypoint)-pose["p"])>.45:setpoint=np.array(waypoint);break
                camera_stale=frame is None or (time.monotonic_ns()-frame["wall_ns"])/1e9>.35
                if camera_stale and decision["phase"] not in ("RETOUR_BASE","POSE"):setpoint=pose["p"].copy()
                tracks=list(self.ai.perception.tracks.values())
                for track in tracks:
                    prior=self.reported_tracks.get(track['id'])
                    if track['seen_count']<2:continue
                    if prior is None or (t-prior[0]>10 and np.linalg.norm(np.asarray(track['position'])-prior[1])>.3):
                        self.emit('object_detected' if prior is None else 'object_updated',
                                  {'id':track['id'],'class':track['class'],'p':np.round(track['position'],2).tolist(),
                                   'confidence':round(track['confidence'],3)},t)
                        self.reported_tracks[track['id']]=(t,np.asarray(track['position']).copy())
                zones=[[*track["position"][:2],1.8] for track in tracks if track["class"] in ("mine","weapon","hostile_unit")]
                control_data={"p":setpoint.round(3).tolist(),"phase":decision["phase"],"valid_until":int((absolute+.65)*1000),"zones":zones[:8]}
                control_data['hold']=len(route)<=1 or (camera_stale and decision['phase'] not in ('RETOUR_BASE','POSE'))
                # With a downward camera, forward range is the VERTICAL half
                # footprint. Bound speed so braking fits before a new hazard.
                horizon=max(0.,float(pose['p'][2]))*math.tan(.6)*.75
                usable=max(0.,horizon-2.35-.55)
                # Solve v^2/(2a)+reaction*v <= usable, with a=1.5,
                # conservative reaction=.3s. This does not certify recall.
                perception_speed=min(.9,max(0.,math.sqrt(.45**2+3.*usable)-.45))
                control_data['speed_limit']=round(perception_speed,3)
                control_data["available_wh"]=round(self.battery.remaining_wh,4)
                if self.fault_next:control_data["fault_inject"]=True;self.fault_next=False
                packet=self.codec.encode(envelope(self.id,self.session,"command",int(t*1000)+1,t,"setpoint",control_data))
                self.control_pub.publish(StringMsg(data=packet.decode()))
                self.pipeline_times.append((time.monotonic_ns()-frame["wall_ns"])/1e6 if frame else 0)
                request=decision.get("request_delivery")
                if request and request["request_id"] not in self.delivered:
                    key=request["request_id"]
                    if np.linalg.norm(pose["v"])<.2:
                        self.delivery_dwell.setdefault(key,t)
                        if t-self.delivery_dwell[key]>1:
                            # First integration gate is a virtual supply delivery.
                            # A separately evaluated physical-drop backend follows.
                            self.delivered.add(key);self.supply_count-=1
                            self.emit("delivery_completed",{"target_track_id":request["target_track_id"],"mode":"virtual_hover_delivery"},t)
                    else:self.delivery_dwell.pop(key,None)
                detail=decision["decision_details"]
                status={"t":round(t,2),"phase":decision["phase"],"p":pose["p"].round(3).tolist(),
                        "energy":round(self.battery.remaining_wh,3),"return_threshold":detail.get("return_threshold_wh"),
                        "served":len(self.delivered),"pending_events":len(self.radio.events),"goal_revision":self.goal_revision}
                self.radio.publish_status(status,t)
                if t-self.last_checkpoint>=5:
                    self.emit('mission_checkpoint',{'p':status['p'],'energy':status['energy'],
                        'phase':status['phase'],'served':status['served']},t)
                    self.last_checkpoint=t
                diagnostic={**status,"mission_id":self.id,"decision":decision["decision_code"],"explanation":"Medical urgency dominates safe travel time. Rescue feasibility includes outbound, delivery, return and reserve.",
                    "wind_speed":float(np.linalg.norm(self.bus.wind)),"ai_p95_ms":float(np.percentile(self.ai_times,95)),
                    "pipeline_p95_ms":float(np.percentile(self.pipeline_times,95)),"control":self.control,
                    "security":dict(self.radio.counters),"route":route,"obstacles":observed,
                    "tracks":[{**track,"served":track["id"] in self.ai.planner.served} for track in tracks],"model_domain":"synthetic_role_cues"}
                atomic_json(self.out/"onboard.json",diagnostic)
                self.trace.append({"t":t,"p":pose["p"].tolist(),"energy":self.battery.remaining_wh,"phase":decision["phase"]})
                if decision["phase"]=="POSE":
                    self.emit("mission_landed",{"deliveries":len(self.delivered),"at_base":not self.emergency},t);time.sleep(1);break
            if t>360:self.emit("mission_timeout",{},t);break
            time.sleep(max(0,.05-(time.monotonic()-begin)))
        (self.log_dir/"trace.json").write_text(json.dumps(clean(self.trace)))
        from .evaluation import evaluate_trace
        scenario=json.loads((ROOT/'sim/generated/coast.json').read_text())
        (self.log_dir/'evaluation.json').write_text(json.dumps(evaluate_trace(self.trace,scenario),indent=2))
        self.log.close();self.radio.close()


if __name__=="__main__":
    runtime=Runtime()
    signal.signal(signal.SIGINT,lambda *_:setattr(runtime,"running",False))
    signal.signal(signal.SIGTERM,lambda *_:setattr(runtime,"running",False))
    runtime.run()
