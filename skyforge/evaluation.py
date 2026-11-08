"""Independent geometric checks against evaluator-only scenario truth.

This checks a conservative spherical vehicle envelope. It is not a replacement
for contact sensors, and cannot certify unobserved dynamic-obstacle contacts.
"""
import math
import numpy as np


def segment_distance(a,b,p):
    a=np.asarray(a,float);b=np.asarray(b,float);p=np.asarray(p,float)
    delta=b-a;den=float(delta@delta)
    u=np.clip(float((p-a)@delta)/den,0,1) if den>1e-12 else 0
    return float(np.linalg.norm(p-a-u*delta))


def evaluate_trace(trace,scenario,vehicle_radius=.35):
    hazards=[e for e in scenario['entities'] if e['class'] in ('mine','weapon','hostile_unit')]
    minima={e['id']:math.inf for e in hazards};entries={e['id']:0 for e in hazards}
    occupied={e['id']:False for e in hazards};zone_seconds=0.;path_length=0.;collision_segments=0
    for previous,current in zip(trace,trace[1:]):
        a=np.array(previous['p'],float);b=np.array(current['p'],float)
        dt=max(0,float(current['t'])-float(previous['t']));path_length+=float(np.linalg.norm(b-a))
        any_zone=False
        for hazard in hazards:
            distance=segment_distance(a[:2],b[:2],hazard['position'][:2])
            minima[hazard['id']]=min(minima[hazard['id']],distance)
            in_zone=distance < 1.8+vehicle_radius
            if in_zone and not occupied[hazard['id']]:entries[hazard['id']]+=1
            occupied[hazard['id']]=in_zone;any_zone|=in_zone
        if any_zone:zone_seconds+=dt
        # Swept sampling bounds inter-sample tunnelling through static boxes.
        steps=max(2,math.ceil(float(np.linalg.norm(b-a))/.1)+1)
        collided=False
        for point in np.linspace(a,b,steps):
            for obstacle in scenario['obstacles']:
                center=np.asarray(obstacle['center']);half=np.asarray(obstacle['size'])/2
                nearest=np.clip(point,center-half,center+half)
                if np.linalg.norm(point-nearest)<vehicle_radius:collided=True
        collision_segments+=int(collided)
    final=trace[-1] if trace else None;base=np.asarray(scenario['base'])
    at_base=bool(final and np.linalg.norm(np.asarray(final['p'])[:2]-base[:2])<.8 and final['p'][2]<.25)
    return {'samples':len(trace),'duration_sim_s':float(final['t']) if final else 0,
            'path_length_m':path_length,'zone_entries':entries,'zone_occupied_seconds_upper_estimate':zone_seconds,
            'minimum_hazard_center_distance_m':{k:v if math.isfinite(v) else None for k,v in minima.items()},
            'static_collision_segments':collision_segments,'landed_at_base':at_base,
            'final_energy_wh':final.get('energy') if final else None,
            'scope':'Swept trace against declared static geometry and hazard cylinders; dynamic contacts and physical payload delivery not certified.'}
