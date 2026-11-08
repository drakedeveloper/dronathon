"""Pin published model inputs and generate one auditable physical reference."""
import hashlib
import json
import math
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
from skyforge.airframe import composite_mass_properties,box_inertia

ROOT=Path(__file__).resolve().parents[1];out=ROOT/'configs/airframes';out.mkdir(parents=True,exist_ok=True)
api='https://api.github.com/repos/PX4/PX4-gazebo-models/commits/main'
commit=json.load(urllib.request.urlopen(api,timeout=20))['sha']
sources={};trees={}
for name,path in [('base','models/x500_base/model.sdf'),('motors','models/x500/model.sdf')]:
    url=f'https://raw.githubusercontent.com/PX4/PX4-gazebo-models/{commit}/{path}'
    body=urllib.request.urlopen(url,timeout=20).read();trees[name]=ET.fromstring(body)
    sources[name]={'url':url,'sha256':hashlib.sha256(body).hexdigest()}
components=[];rotors=[]
motor_plugins=trees['motors'].find('model').findall('plugin')
motor_plugins=[p for p in motor_plugins if p.find('motorConstant') is not None]
for link in trees['base'].find('model').findall('link'):
    inertial=link.find('inertial')
    if inertial is None:continue
    mass=float(inertial.findtext('mass'));position=list(map(float,(link.findtext('pose') or '0 0 0 0 0 0').split()))[:3]
    tensor=inertial.find('inertia');matrix=np.array([[float(tensor.findtext('i'+a+b) or tensor.findtext('i'+b+a) or '0') for b in 'xyz'] for a in 'xyz'])
    components.append({'id':link.attrib['name'],'mass_kg':mass,'position_flu_m':position,
        'inertia_at_own_cg_kg_m2':matrix.tolist(),'basis':'Published PX4 simulator aggregate, not measured team hardware'})
    if link.attrib['name'].startswith('rotor_'):
        index=int(link.attrib['name'].split('_')[1]);p=motor_plugins[index]
        rotors.append({'id':index,'position_flu_m':position,'spin_viewed_from_above':p.findtext('turningDirection')})
for identity,mass,position,dimensions in [('medical_kits_total',.15,[0,0,-.14],[.20,.14,.06]),('mount',.04,[0,0,-.09],[.24,.18,.02])]:
    components.append({'id':identity,'mass_kg':mass,'position_flu_m':position,
        'inertia_at_own_cg_kg_m2':box_inertia(mass,dimensions),
        'basis':'Selected design allowance, unmeasured; kits are3x50g simulation payloads'})
derived=composite_mass_properties(components);motor=motor_plugins[0]
kt=float(motor.findtext('motorConstant'));omega=float(motor.findtext('maxRotVelocity'))
rho=1.225;diameter=.28;weight=derived['mass_kg']*9.80665;max_thrust=4*kt*omega**2
derived.update(max_total_thrust_n=max_thrust,thrust_to_weight=max_thrust/weight,
    hover_omega_rad_s=math.sqrt(weight/(4*kt)),hover_rpm=math.sqrt(weight/(4*kt))*60/(2*math.pi))
profile={'schema_version':1,'name':'SKYFORGE X500-class research rescue reference',
    'status':'Source-backed simulator reference plus declared payload assumptions; NOT physical-hardware calibrated',
    'sources':sources,'upstream_commit':commit,'components':components,'rotors':rotors,'derived':derived,
    'motor':{'thrust_coefficient_n_per_rad_s_squared':kt,'torque_to_thrust_m':float(motor.findtext('momentConstant')),
        'max_omega_rad_s':omega,'time_constant_up_s':float(motor.findtext('timeConstantUp')),
        'time_constant_down_s':float(motor.findtext('timeConstantDown'))},
    'propeller':{'diameter_m':diameter,'basis':'Selected11-inch-class design assumption; verify against actual purchased propeller'},
    'atmosphere':{'rho_kg_m3':rho,'gravity_m_s2':9.80665},
    'battery':{'series_cells':4,'nominal_voltage_v':14.8,'capacity_ah':5.,'nominal_energy_wh':74.,
        'usable_fraction':.8,'mission_energy_allowance_wh':15.,
        'basis':'Selected4S5000mAh pack;15Wh mission allowance is separate from electrical capacity; no sag calibration yet'},
    'unverified':['Specific hardware BOM price','Actual component masses and CG','Propeller thrust/torque bench curves',
        'Measured inertia','Airframe drag/wake','Battery internal resistance and sag','Sensor noise/latency','Rotor acoustic performance']}
(out/'x500-research.json').write_text(json.dumps(profile,indent=2));print(json.dumps(derived,indent=2))
