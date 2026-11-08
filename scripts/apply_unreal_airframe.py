"""Generate AirSim physics parameters from the auditable reference JSON.

Patches only our downloaded plugin copy, which is rebuilt against the installed
engine. Does not change the original packaged Coastline executable.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
from skyforge.airframe import load_airframe

ROOT=Path(__file__).resolve().parents[1]
profile=load_airframe(ROOT/'configs/airframes/x500-research.json')
include=ROOT/'runtime/unreal/SKYFORGE/Plugins/AirSim/Source/AirLib/include/vehicles/multirotor'
target=include/'firmwares/simple_flight/SimpleFlightQuadXParams.hpp'
if not target.exists():raise FileNotFoundError('Run setup_unreal_plugin.ps1 first')
motor=profile['motor'];rho=profile['atmosphere']['rho_kg_m3'];diameter=profile['propeller']['diameter_m']
kt=motor['thrust_coefficient_n_per_rad_s_squared'];kq=kt*motor['torque_to_thrust_m']
ct=kt*(2*math.pi)**2/(rho*diameter**4);cp=kq*(2*math.pi)**3/(rho*diameter**5)
frame=np.diag([1.,-1.,-1.]);inertia=frame@np.asarray(profile['derived']['inertia_about_cg_flu_kg_m2'])@frame
cg=np.asarray(profile['derived']['cg_flu_m']);mass=profile['derived']['mass_kg']
lines=['// Generated from configs/airframes/x500-research.json; not measured hardware calibration.',
       '#pragma once','namespace msr { namespace airlib {',
       'inline void setupSkyforgeReference(MultiRotorParams::Params& p) {',
       f' p.rotor_count=4; p.mass={mass:.12g}f;',
       ' p.body_box=Vector3r(0.35355339f,0.35355339f,0.05f);',
       ' p.inertia.setZero();']
def cppfloat(value):return f'{float(value):.12e}f'
for i in range(3):
    for j in range(3):lines.append(f' p.inertia({i},{j})={cppfloat(inertia[i,j])};')
lines += [f' p.rotor_params.C_T={cppfloat(ct)};',f' p.rotor_params.C_P={cppfloat(cp)};',
          f' p.rotor_params.air_density={cppfloat(rho)};',
          f' p.rotor_params.propeller_diameter={cppfloat(diameter)};',
          f' p.rotor_params.max_rpm={cppfloat(motor["max_omega_rad_s"]*60/(2*math.pi))};',
          f' p.rotor_params.control_signal_filter_tc={cppfloat(motor["time_constant_down_s"])};',
          ' p.rotor_params.calculateMaxThrust();',' p.rotor_poses.clear();']
for rotor in profile['rotors']:
    p=frame@(np.asarray(rotor['position_flu_m'])-cg)
    direction='RotorTurningDirectionCCW' if rotor['spin_viewed_from_above']=='ccw' else 'RotorTurningDirectionCW'
    vector=','.join(cppfloat(v) for v in p)
    lines.append(f' p.rotor_poses.emplace_back(Vector3r({vector}),Vector3r(0,0,-1),RotorTurningDirection::{direction});')
# Match the declared horizontal CdA using the simulator's own exposed-area law.
# The built-in vertical drag remains different; it is listed as a model limit.
area=.35355339*.05+4*math.pi*diameter*.01
lines += [f' p.linear_drag_coefficient={cppfloat(.045/area)};',' p.angular_drag_coefficient=0.08f;',
          ' p.restitution=0.05f; p.friction=0.6f;','}', '} }']
header=include/'SkyforgeReference.hpp';header.write_text('\n'.join(lines)+'\n')
body=target.read_text()
if '#include "vehicles/multirotor/SkyforgeReference.hpp"' not in body:
    body=body.replace('#include "vehicles/multirotor/MultiRotorParams.hpp"',
        '#include "vehicles/multirotor/MultiRotorParams.hpp"\n#include "vehicles/multirotor/SkyforgeReference.hpp"')
if 'setupFrameGenericQuad(params);' in body:body=body.replace('setupFrameGenericQuad(params);','setupSkyforgeReference(params);')
elif 'setupSkyforgeReference(params);' not in body:raise ValueError('Upstream setup function changed; review before patching')
target.write_text(body)
manifest={'profile_sha256':hashlib.sha256((ROOT/'configs/airframes/x500-research.json').read_bytes()).hexdigest(),
    'mass_kg':mass,'C_T':ct,'C_P':cp,'expected_max_thrust_per_rotor_n':kt*motor['max_omega_rad_s']**2,
    'limits':['Published simulator mass/inertia plus payload assumptions, not measured hardware',
              'Symmetric25ms motor filter used, whereas source specifies12.5ms up/25ms down',
              'Vertical/body drag and wake models require calibration','Battery sag not modeled by this patch',
              'Original stock drone visual/collision mesh is not yet replaced by the reference airframe geometry']}
(ROOT/'runtime/unreal/SKYFORGE/airframe-build.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
