"""Bounded geometric routing, medical ranking and two-agent LangGraph."""
from dataclasses import dataclass
import heapq
import math
import time
import numpy as np
from .physics import Vehicle,route_energy
from .vision import localize,ground_point_visible,ground_depth_difference


@dataclass
class Circle:
    x:float
    y:float
    radius:float
    kind:str="obstacle"


def segment_clear(a,b,circles,margin=.55):
    ax,ay=float(a[0]),float(a[1]);dx=float(b[0])-ax;dy=float(b[1])-ay
    length2=dx*dx+dy*dy
    for c in circles:
        px=c.x-ax;py=c.y-ay
        u=max(0.,min(1.,(px*dx+py*dy)/length2)) if length2>1e-12 else 0.
        if (px-u*dx)**2+(py-u*dy)**2<=(c.radius+margin)**2:return False
    return True


def astar(start,goal,circles,bounds=(-15,-12,15,12),resolution=.5,altitude=6.,budget_ms=35.,_deadline=None):
    deadline=time.perf_counter()+budget_ms/1000 if _deadline is None else _deadline
    if time.perf_counter()>deadline:return None
    start=np.asarray(start,float);goal=np.asarray(goal,float)
    if not np.all(np.isfinite([*start,*goal])):return None
    xmin,ymin,xmax,ymax=bounds
    def cell(p):return (round((p[0]-xmin)/resolution),round((p[1]-ymin)/resolution))
    def point(c):return (xmin+c[0]*resolution,ymin+c[1]*resolution,altitude)
    def inside(p):return xmin+.55<=p[0]<=xmax-.55 and ymin+.55<=p[1]<=ymax-.55
    if not inside(goal):return None
    containing=[c for c in circles if np.linalg.norm(start[:2]-[c.x,c.y])<=c.radius+.55]
    if containing:
        # Recovery only: if a newly observed exclusion inflation already
        # contains us, exit monotonically away rather than deadlocking. The
        # evaluator must still record the initial zone-entry violation.
        for angle in np.linspace(0,2*math.pi,24,endpoint=False):
            if time.perf_counter()>deadline:return None
            direction=np.array([math.cos(angle),math.sin(angle)])
            if any(direction@(start[:2]-[c.x,c.y])<=0 for c in containing):continue
            for distance in (1.,2.,3.,4.):
                escape=np.r_[start[:2]+distance*direction,altitude]
                if not inside(escape):continue
                if any(np.linalg.norm(escape[:2]-[c.x,c.y])<=c.radius+.65 for c in circles):continue
                others=[c for c in circles if c not in containing]
                if not segment_clear(start,escape,others):continue
                continuation=astar(escape,goal,circles,bounds,resolution,altitude,budget_ms,deadline)
                if continuation:return [start.tolist(),escape.tolist(),*continuation[1:]]
        return None
    def with_ascent(route):
        if abs(start[2]-altitude)>.5 and np.linalg.norm(start[:2]-goal[:2])>.5:
            return [route[0],[float(start[0]),float(start[1]),altitude],*route[1:]]
        return route
    if segment_clear(start,goal,circles):return with_ascent([start.tolist(),[float(goal[0]),float(goal[1]),altitude]])
    origin=cell(start);target=cell(goal);q=[(0.,origin)];parent={origin:None};cost={origin:0.};closed=set()
    while q:
        if time.perf_counter()>deadline:return None
        _,current=heapq.heappop(q)
        if current in closed:continue
        closed.add(current)
        if current==target:
            chain=[]
            while current is not None:chain.append(list(point(current)));current=parent[current]
            chain.reverse();chain[0]=start.tolist();chain[-1]=[float(goal[0]),float(goal[1]),altitude]
            # Shortcut only through explicitly checked collision-free segments.
            output=[chain[0]];i=0
            while i<len(chain)-1:
                j=len(chain)-1
                while j>i+1 and not segment_clear(chain[i],chain[j],circles):j-=1
                output.append(chain[j]);i=j
            return with_ascent(output)
        # Grid rounding may put the origin cell centre inside an obstacle
        # even when the physical start is clear. Connect the actual endpoint.
        current_point=start if current==origin else point(current)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            nxt=(current[0]+dx,current[1]+dy)
            if nxt in closed:continue
            p=goal if nxt==target else point(nxt)
            if not inside(p) or not segment_clear(current_point,p,circles):continue
            nc=cost[current]+math.hypot(dx,dy)
            if nc>=cost.get(nxt,math.inf):continue
            cost[nxt]=nc;parent[nxt]=current
            heuristic=math.hypot(nxt[0]-target[0],nxt[1]-target[1])
            heapq.heappush(q,(nc+heuristic,nxt))
    return None


def rank_casualties(candidates):
    """Urgency dominates proximity; infeasible candidates are never selected."""
    feasible=[c for c in candidates if c["feasible"]]
    return sorted(feasible,key=lambda c:(-c["urgency"],c["travel_s"],c["id"]))


class PerceptionAgent:
    def __init__(self):self.tracks={};self.next_id=1;self.last_frame=-1

    def update(self,snapshot):
        frame=snapshot.get("frame");batch=snapshot.get("detections")
        if frame is None or batch is None or batch["frame_id"]==self.last_frame:return self.tracks
        self.last_frame=batch["frame_id"]
        seen=set()
        for detection in batch["detections"]:
            # Confidence scales differ between the pixel baseline and YOLO.
            # Low-confidence hazards enlarge the map conservatively; casualty
            # selection still requires repeated spatially consistent sightings.
            minimum=.35
            if detection["confidence"]<minimum:continue
            p=localize(detection,frame)
            if p is None or not np.all(np.isfinite(p)) or p[2]>2.5:continue
            # All current props/casualties are supported on the coastal surface.
            p[2]=0.
            people=('injured_person','hostile_unit')
            matches=[t for t in self.tracks.values() if (t['class']==detection['class'] or
                t['class'] in people and detection['class'] in people) and np.linalg.norm(np.array(t["position"])[:2]-p[:2])<1.25]
            if matches:
                track=min(matches,key=lambda t:np.linalg.norm(np.array(t["position"])[:2]-p[:2]))
                if track.get('invalidated'):track['seen_count']=0;track['class_votes']={}
                track["position"]=(.7*np.array(track["position"])+.3*p).tolist()
                track["seen_count"]+=1;track["last_seen"]=frame["t"]
                track['invalidated']=False;track['visible_misses']=0;seen.add(track['id'])
            else:
                identity=f"track-{self.next_id:04}";self.next_id+=1
                self.tracks[identity]={"id":identity,"class":detection["class"],"position":p.tolist(),
                                       "seen_count":1,"last_seen":frame["t"],"confidence":detection["confidence"]}
                track=self.tracks[identity]
                seen.add(identity)
            if detection['class'] in people:
                votes=track.setdefault('class_votes',{})
                votes[detection['class']]=votes.get(detection['class'],0.)+float(detection['confidence'])
                winner=max(votes,key=votes.get);share=votes[winner]/sum(votes.values())
                track['class']=winner;track['class_vote_share']=share
                track['classification_uncertain']=share<.7 or sum(votes.values())<1.
        for identity,track in self.tracks.items():
            if track['class']=='injured_person':
                height=ground_depth_difference(track['position'],frame)
                if height is not None and .075<height<.7:
                    track['depth_presence_t']=frame['t']
                    if track['seen_count']>=3:
                        track['invalidated']=False;track['visible_misses']=0
            if track['class']=='injured_person' and identity not in seen and ground_point_visible(track['position'],frame):
                track['visible_misses']=track.get('visible_misses',0)+1
                if track['visible_misses']>=5:track['invalidated']=True
        return self.tracks


class PlannerAgent:
    def __init__(self,config):
        self.config=config;self.vehicle=config.get('vehicle',Vehicle());self.phase="INIT";self.served=set();self.goal=None
        self.altitude=float(config.get('survey_altitude_m',8.))
        self.coverage=[]
        # At8 m the ground footprint is ~10.95 x8.21 m (640x480,
        # HFOV1.2). Six-metre row spacing retains overlap and lookahead.
        for row,y in enumerate(np.arange(-8,10.1,6)):
            xs=(-11.,11.) if row%2==0 else (11.,-11.)
            self.coverage.extend([[x,float(y),self.altitude] for x in xs])
        self.coverage_index=0;self.return_latched=False;self.last_goal_revision=-1
        self.beacon_inspected=set();self.beacon_arrival={}
        self.last_return_threshold=config.get("reserve_wh",1.)+.12

    def energy_for_route(self,path,wind,landing=False):
        """Budget the commanded slow mission, including settling and descent.

        Previous estimates used2 m/s while safety limited flight to0.9 m/s.
        Use0.65 m/s expected progress and0.5 m/s vertical progress; retain the
        wind feasibility check and conservative hover-power floor.
        """
        nominal,_=route_energy(self.vehicle,path,wind,uncertainty_m_s=.3,ground_speed_limit=.65)
        duration=0.;climb=0.
        for a,b in zip(path,path[1:]):
            delta=np.asarray(b)-a
            duration+=np.linalg.norm(delta[:2])/.65+abs(delta[2])/.5+2.
            climb+=max(0.,delta[2])
        if landing:duration+=self.altitude/.5+8.
        power=max(self.vehicle.power_w(0),self.vehicle.power_w(float(np.linalg.norm(wind))))
        estimate=power*duration/3600+self.vehicle.weight_n*climb/self.vehicle.induced_efficiency/3600
        return max(nominal,estimate),duration

    def plan(self,snapshot,tracks):
        pos=np.asarray(snapshot["position_enu_m"],float);base=np.asarray(snapshot["base_enu_m"],float)
        wind=snapshot.get("wind_enu_mps",[0,0,0]);energy=snapshot["battery_wh"]
        circles=[Circle(**c) for c in snapshot.get("obstacle_circles",[])]
        for t in tracks.values():
            if t["class"] in ("mine","weapon","hostile_unit") or t.get('classification_uncertain'):
                circles.append(Circle(*t["position"][:2],1.8,"hazard"))
        return_path=astar(pos,base,circles,altitude=self.altitude)
        reserve=self.config.get("reserve_wh",1.)
        return_energy=self.energy_for_route(return_path,wind,landing=True)[0] if return_path else math.inf
        threshold=return_energy*1.2+reserve+.12 if math.isfinite(return_energy) else self.last_return_threshold
        if math.isfinite(return_energy):self.last_return_threshold=threshold
        if energy<=threshold and pos[2]>.5:self.return_latched=True
        for event in snapshot.get("events",[]):
            if event.get("type")=="delivery_completed":self.served.add(event["target_track_id"]);self.goal=None
        if snapshot.get('supply_count',1)<=0:self.return_latched=True
        detail={"return_energy_wh":return_energy,"return_threshold_wh":threshold,"available_energy_wh":energy,"candidates":[]}
        if return_path is None:
            return {"v":1,"snapshot_seq":snapshot["snapshot_seq"],"goal_revision":snapshot.get("goal_revision",0),
                    "map_revision":snapshot.get("map_revision",0),"phase":"RETOUR_BASE" if self.return_latched else "TRIAGE",
                    "target_track_id":None,"waypoints_enu_m":[pos.tolist()],"return_path_enu_m":[],"request_delivery":None,
                    "decision_code":"TEMPORARY_RETURN_ROUTE_BLOCKED_HOLD","decision_details":detail}
        target=None;path=None;delivery=None;code="EXPLORE_UNSEEN_AREA"
        if self.return_latched:
            self.phase="RETOUR_BASE";code="SUPPLIES_DELIVERED_RETURN" if snapshot.get('supply_count',1)<=0 else "DYNAMIC_ENERGY_RETURN";path=return_path
        elif pos[2]<self.altitude-.5 and self.phase=="INIT":
            path=[pos.tolist(),[pos[0],pos[1],self.altitude]];code="TAKEOFF_TO_SURVEY_ALTITUDE"
        else:
            candidates=[]
            for t in tracks.values():
                if t["class"]!="injured_person" or t["seen_count"]<2 or t.get('invalidated') or t.get('classification_uncertain') or t["id"] in self.served:continue
                p=np.array(t["position"]);p[2]=self.altitude
                outbound=astar(pos,p,circles,altitude=self.altitude)
                inbound=astar(p,base,circles,altitude=self.altitude)
                travel=math.inf;required=math.inf
                if outbound and inbound:
                    eo,travel=self.energy_for_route(outbound,wind)
                    er,_=self.energy_for_route(inbound,wind,landing=True)
                    delivery_seconds=2*max(0,self.altitude-2.2)/.5+8.
                    delivery_energy=self.vehicle.power_w(0)*delivery_seconds/3600
                    required=(eo+er+delivery_energy)*1.2+reserve
                urgency=1;source="unknown_default"
                for beacon in snapshot.get("urgency_observations",[]):
                    if np.linalg.norm(np.array(beacon["position"])[:2]-p[:2])<1.5:
                        urgency=beacon["urgency"];source=beacon["source"];break
                item={"id":t["id"],"urgency":urgency,"urgency_source":source,"travel_s":travel,
                      "required_energy_wh":required,"feasible":required<=energy,"path":outbound}
                candidates.append(item)
            detail["candidates"]=[{k:v for k,v in c.items() if k!="path"} for c in candidates]
            ranked=rank_casualties(candidates)
            if ranked and snapshot.get("supply_count",0)>0:
                chosen=ranked[0];target=chosen["id"];t=tracks[target];path=chosen["path"]
                self.phase="NAVIGUER";code="HIGHEST_URGENCY_FEASIBLE"
                distance=np.linalg.norm(pos[:2]-np.array(t["position"])[:2])
                if distance<.6:
                    self.phase="LIVRER";path=[pos.tolist(),[*t["position"][:2],2.2]]
                    now=snapshot.get('frame',{}).get('t',t['last_seen'])
                    fresh=now-t['last_seen']<1. or t['seen_count']>=3 and now-t.get('depth_presence_t',-1e30)<.4
                    if abs(pos[2]-2.2)<.3 and fresh:
                        delivery={"request_id":f"aid-{target}","target_track_id":target}
            else:
                self.phase="EXPLORER"
                revision=snapshot.get("goal_revision",0)
                update=snapshot.get("goal_update")
                if update and update.get("position") and revision>self.last_goal_revision:
                    path=astar(pos,update["position"],circles,altitude=self.altitude);code="GROUND_STATION_REROUTE"
                    if np.linalg.norm(pos[:2]-np.array(update["position"])[:2])<.8:
                        self.last_goal_revision=revision;path=None
                if not path:
                    # Distress-radio observations are an explicit scenario
                    # input, not hidden world truth. Investigate highest urgency
                    # before spending energy on a blind sweep. A beacon never
                    # authorizes delivery without visual confirmation.
                    beacons=sorted(snapshot.get('urgency_observations',[]),
                        key=lambda b:(-b.get('urgency',1),math.dist(pos[:2],b['position'][:2])))
                    for beacon in beacons:
                        p=np.array(beacon['position'],float);p[2]=self.altitude
                        identity=tuple(round(float(v),2) for v in p[:2])
                        confirmed=any(t['class']=='injured_person' and t['seen_count']>=2 and not t.get('invalidated')
                            and math.dist(t['position'][:2],p[:2])<1.5 for t in tracks.values())
                        if confirmed:self.beacon_inspected.add(identity)
                        if identity in self.beacon_inspected:continue
                        if math.dist(pos[:2],p[:2])<.7:
                            now=snapshot.get('t_sim_s',0.)
                            self.beacon_arrival.setdefault(identity,now)
                            if now-self.beacon_arrival[identity]>=2.:
                                self.beacon_inspected.add(identity);continue
                        path=astar(pos,p,circles,altitude=self.altitude)
                        code='INVESTIGATE_DISTRESS_BEACON' if path else 'BEACON_ROUTE_PENDING_HOLD'
                        break
                if not path:
                    if code=='BEACON_ROUTE_PENDING_HOLD':
                        path=[pos.tolist()]
                if not path:
                    while self.coverage_index<len(self.coverage):
                        candidate=self.coverage[self.coverage_index]
                        if np.linalg.norm(pos[:2]-np.array(candidate)[:2])<.7:self.coverage_index+=1;continue
                        if any(math.hypot(candidate[0]-c.x,candidate[1]-c.y)<=c.radius+.55 for c in circles):
                            self.coverage_index+=1;continue
                        path=astar(pos,candidate,circles,altitude=self.altitude)
                        # A time-budget failure is not evidence of survey
                        # completion. Preserve this objective and retry.
                        if not path:code='COVERAGE_ROUTE_PENDING_HOLD'
                        break
                if not path and self.coverage_index>=len(self.coverage):
                    self.phase="RETOUR_BASE";self.return_latched=True;path=return_path;code="SURVEY_COMPLETE_RETURN"
        if self.phase=="RETOUR_BASE" and np.linalg.norm(pos[:2]-base[:2])<.6:
            path=[pos.tolist(),[float(base[0]),float(base[1]),.08]]
            if pos[2]<.17:self.phase="POSE";code="LANDED"
        if not path:
            path=[pos.tolist()]
            if code!='COVERAGE_ROUTE_PENDING_HOLD':code="NO_SAFE_ROUTE_HOLD"
        return {"v":1,"snapshot_seq":snapshot["snapshot_seq"],"goal_revision":snapshot.get("goal_revision",0),
                "map_revision":snapshot.get("map_revision",0),"phase":self.phase,"target_track_id":target,
                "waypoints_enu_m":path,"return_path_enu_m":return_path or [],"request_delivery":delivery,
                "decision_code":code,"decision_details":detail}


class MissionAI:
    def __init__(self,config):
        from langgraph.graph import StateGraph,START,END
        from typing import TypedDict
        self.perception=PerceptionAgent();self.planner=PlannerAgent(config)
        class State(TypedDict):
            snapshot:dict
            tracks:dict
            decision:dict
        graph=StateGraph(State)
        graph.add_node("PerceptionAgent",lambda s:{"tracks":self.perception.update(s["snapshot"])})
        graph.add_node("PlannerAgent",lambda s:{"decision":self.planner.plan(s["snapshot"],s["tracks"])})
        graph.add_edge(START,"PerceptionAgent");graph.add_edge("PerceptionAgent","PlannerAgent");graph.add_edge("PlannerAgent",END)
        self.graph=graph.compile()

    def step(self,snapshot):return self.graph.invoke({"snapshot":snapshot,"tracks":{},"decision":{}})["decision"]

    def reset(self,mission_id):self.__init__(self.planner.config)
