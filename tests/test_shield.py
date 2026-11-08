import numpy as np
from skyforge.planning import Circle
from skyforge.shield import route_violations,apply_shield


def test_route_through_hazard_is_rejected_even_with_clear_endpoints():
    assert route_violations([[-4,0,8],[4,0,8]],[-4,0,8],[Circle(0,0,1.8,'hazard')])==['ROUTE_INTERSECTS_HAZARD']


def test_monotonic_escape_allowed_but_deeper_entry_rejected():
    circles=[Circle(0,0,1.8,'hazard')]
    assert route_violations([[1,0,8],[3,0,8]],[1,0,8],circles)==[]
    assert route_violations([[1,0,8],[-3,0,8]],[1,0,8],circles)


def test_nonfinite_plan_cannot_reach_controller():
    assert route_violations([[0,0,8],[np.nan,2,8]],[0,0,8],[])==['NONFINITE_WAYPOINT']


def test_low_energy_overrules_exploration_and_cancels_delivery():
    snapshot={'position_enu_m':[0,0,8],'battery_wh':2,'obstacle_circles':[]}
    decision={'phase':'EXPLORER','waypoints_enu_m':[[0,0,8],[10,0,8]],
              'return_path_enu_m':[[0,0,8],[-12,-9,8]],'request_delivery':{'request_id':'bad'},
              'decision_details':{'return_threshold_wh':3}}
    safe=apply_shield(snapshot,decision,{})
    assert safe['phase']=='RETOUR_BASE' and safe['request_delivery'] is None
    assert decision['phase']=='EXPLORER'
