"""Independent deterministic route shield; no neural model or LLM.

Checks declared geometric constraints. This is not a formal control barrier
function proof and cannot reject an obstacle that was never sensed/mapped.
"""
import copy
import math
import numpy as np
from .planning import Circle,segment_clear


def route_violations(route,position,circles,bounds=(-15,-12,15,12),margin=.55):
    try:points=np.asarray(route,dtype=float)
    except (TypeError,ValueError):return ['INVALID_ROUTE_SHAPE']
    if points.ndim!=2 or points.shape[1]!=3 or not 1<=len(points)<=128:return ['INVALID_ROUTE_SHAPE']
    if not np.all(np.isfinite(points)):return ['NONFINITE_WAYPOINT']
    if np.linalg.norm(points[0]-position)>.8:return ['STALE_ROUTE_ORIGIN']
    xmin,ymin,xmax,ymax=bounds
    if any(not(xmin+.35<=p[0]<=xmax-.35 and ymin+.35<=p[1]<=ymax-.35 and .0<=p[2]<=12.) for p in points):
        return ['WAYPOINT_OUTSIDE_FLIGHT_ENVELOPE']
    for index,(a,b) in enumerate(zip(points,points[1:])):
        for obstacle in circles:
            if segment_clear(a,b,[obstacle],margin):continue
            # Recovery from a newly observed enclosing zone may move strictly
            # outward. Entry into that zone remains an evaluator violation.
            offset=a[:2]-[obstacle.x,obstacle.y];delta=b[:2]-a[:2]
            inside=np.linalg.norm(offset)<=obstacle.radius+margin
            outward=float(offset@delta)>0
            exited=np.linalg.norm(b[:2]-[obstacle.x,obstacle.y])>obstacle.radius+margin
            if index==0 and inside and outward and exited:continue
            return ['ROUTE_INTERSECTS_'+obstacle.kind.upper()]
    return []


def apply_shield(snapshot,decision,tracks):
    circles=[Circle(**c) for c in snapshot.get('obstacle_circles',[])]
    circles += [Circle(*t['position'][:2],1.8,'hazard') for t in tracks.values()
                if t['class'] in ('mine','weapon','hostile_unit')]
    position=np.asarray(snapshot['position_enu_m'],float)
    violations=route_violations(decision.get('waypoints_enu_m',[]),position,circles)
    threshold=decision.get('decision_details',{}).get('return_threshold_wh')
    energy_override=(isinstance(threshold,(float,int)) and math.isfinite(threshold)
        and snapshot['battery_wh']<=threshold and decision.get('phase') not in ('RETOUR_BASE','POSE'))
    if energy_override:violations.append('RETURN_RESERVE_OVERRIDE')
    if not violations:return decision
    result=copy.deepcopy(decision)
    result['request_delivery']=None;result['target_track_id']=None
    result.setdefault('decision_details',{})['shield_violations']=violations
    returning=result.get('return_path_enu_m')
    if energy_override and returning and not route_violations(returning,position,circles):
        result['waypoints_enu_m']=returning;result['phase']='RETOUR_BASE'
        result['decision_code']='SAFETY_SHIELD_RETURN_OVERRIDE'
    else:
        result['waypoints_enu_m']=[position.tolist()];result['phase']='TRIAGE'
        result['decision_code']='SAFETY_SHIELD_REJECTED_ROUTE'
    return result
