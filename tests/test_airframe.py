import numpy as np
import pytest
from skyforge.airframe import composite_mass_properties,box_inertia


def test_offset_payload_moves_cg_and_increases_parallel_axis_inertia():
    body={'mass_kg':1.,'position_flu_m':[0,0,0],'inertia_at_own_cg_kg_m2':box_inertia(1,[.2,.2,.1])}
    pack={'mass_kg':.2,'position_flu_m':[0,0,-.2],'inertia_at_own_cg_kg_m2':box_inertia(.2,[.1,.1,.1])}
    result=composite_mass_properties([body,pack])
    assert result['mass_kg']==pytest.approx(1.2)
    assert result['cg_flu_m'][2]==pytest.approx(-.04/1.2)
    assert result['inertia_about_cg_flu_kg_m2'][0][0]>body['inertia_at_own_cg_kg_m2'][0][0]+pack['inertia_at_own_cg_kg_m2'][0][0]


def test_invalid_mass_or_nonsymmetric_inertia_is_rejected():
    bad={'mass_kg':-1,'position_flu_m':[0,0,0],'inertia_at_own_cg_kg_m2':np.eye(3).tolist()}
    with pytest.raises(ValueError):composite_mass_properties([bad])
    bad['mass_kg']=1;bad['inertia_at_own_cg_kg_m2'][0][1]=1
    with pytest.raises(ValueError):composite_mass_properties([bad])
