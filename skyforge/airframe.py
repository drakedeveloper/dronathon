"""Mass/CG/inertia accounting and normalized reference-vehicle properties."""
import json
from pathlib import Path
import numpy as np


def composite_mass_properties(components):
    if not components:raise ValueError('Empty mass budget')
    masses=np.array([c['mass_kg'] for c in components],float)
    positions=np.array([c['position_flu_m'] for c in components],float)
    if np.any(masses<=0) or not np.all(np.isfinite(masses)) or positions.shape!=(len(masses),3) or not np.all(np.isfinite(positions)):
        raise ValueError('Invalid mass budget')
    total=float(masses.sum());cg=(masses[:,None]*positions).sum(axis=0)/total
    inertia=np.zeros((3,3))
    for mass,p,component in zip(masses,positions,components):
        intrinsic=np.asarray(component['inertia_at_own_cg_kg_m2'],float)
        if intrinsic.shape!=(3,3) or not np.all(np.isfinite(intrinsic)) or not np.allclose(intrinsic,intrinsic.T):
            raise ValueError('Invalid inertia tensor')
        if np.linalg.eigvalsh(intrinsic).min()<0:raise ValueError('Negative component inertia')
        offset=p-cg;inertia+=intrinsic+mass*((offset@offset)*np.eye(3)-np.outer(offset,offset))
    if np.linalg.eigvalsh(inertia).min()<=0:raise ValueError('Singular composite inertia')
    return {'mass_kg':total,'cg_flu_m':cg.tolist(),'inertia_about_cg_flu_kg_m2':inertia.tolist()}


def box_inertia(mass,dimensions):
    x,y,z=np.asarray(dimensions,float)
    if mass<=0 or min(x,y,z)<=0:raise ValueError('Invalid box')
    return np.diag([mass*(y*y+z*z)/12,mass*(x*x+z*z)/12,mass*(x*x+y*y)/12]).tolist()


def load_airframe(path):
    profile=json.loads(Path(path).read_text())
    calculated=composite_mass_properties(profile['components'])
    if not np.isclose(calculated['mass_kg'],profile['derived']['mass_kg']):raise ValueError('Mass budget mismatch')
    if not np.allclose(calculated['inertia_about_cg_flu_kg_m2'],profile['derived']['inertia_about_cg_flu_kg_m2']):
        raise ValueError('Inertia budget mismatch')
    return profile
