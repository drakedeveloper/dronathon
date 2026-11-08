import numpy as np
from skyforge.planning import Circle,astar,segment_clear,rank_casualties,PlannerAgent


def test_route_avoids_obstacle_and_all_shortcuts_are_checked():
    circles=[Circle(0,0,1)]
    route=astar([-4,0,6],[4,0,6],circles,budget_ms=1000)
    assert route is not None
    assert all(segment_clear(a,b,circles) for a,b in zip(route,route[1:]))


def test_clear_start_near_boundary_is_not_trapped_by_grid_rounding():
    circles=[Circle(-2,-2,2.15),Circle(5,4,1.8)]
    route=astar([-1.65,-4.7,8],[-11,-2,8],circles,budget_ms=1000,altitude=8)
    assert route is not None
    assert all(segment_clear(a,b,circles) for a,b in zip(route,route[1:]))


def test_low_altitude_horizontal_transit_climbs_first():
    route=astar([0,0,2],[5,0,6],[])
    assert route[1]==[0.,0.,6.]


def test_return_budget_accounts_for_slow_cruise_and_landing():
    planner=PlannerAgent({'reserve_wh':1})
    route=[[12,8,8],[-12,-9,8]]
    flight,_=planner.energy_for_route(route,[0,0,0])
    landing,_=planner.energy_for_route(route,[0,0,0],landing=True)
    distance=np.linalg.norm(np.array(route[0])[:2]-np.array(route[1])[:2])
    assert flight>=planner.vehicle.power_w(0)*distance/.65/3600
    assert landing-flight>=planner.vehicle.power_w(0)*23.9/3600


def test_empty_supply_inventory_returns_with_healthy_battery():
    planner=PlannerAgent({'reserve_wh':1})
    state={'position_enu_m':[-10,-8,8],'base_enu_m':[-12,-9,.05],
           'battery_wh':15,'snapshot_seq':1,'obstacle_circles':[],
           'events':[],'supply_count':0}
    decision=planner.plan(state,{})
    assert decision['phase']=='RETOUR_BASE'
    assert decision['decision_code']=='SUPPLIES_DELIVERED_RETURN'
    assert planner.return_latched


def test_radio_distress_beacon_directs_search_but_never_authorizes_delivery():
    planner=PlannerAgent({'reserve_wh':1})
    state={'position_enu_m':[-10,-8,8],'base_enu_m':[-12,-9,.05],
           'battery_wh':15,'snapshot_seq':1,'obstacle_circles':[],
           'events':[],'supply_count':3,'urgency_observations':[
               {'position':[-9,-7,0],'urgency':1,'source':'test_beacon'},
               {'position':[9,-3,0],'urgency':3,'source':'test_beacon'}]}
    decision=planner.plan(state,{})
    assert decision['phase']=='EXPLORER'
    assert decision['decision_code']=='INVESTIGATE_DISTRESS_BEACON'
    assert decision['waypoints_enu_m'][-1]==[9.,-3.,8.]
    assert decision['request_delivery'] is None


def test_urgency_dominates_distance_and_infeasible_is_excluded():
    candidates=[{"id":"near","urgency":1,"travel_s":1,"feasible":True},
                {"id":"critical","urgency":3,"travel_s":40,"feasible":True},
                {"id":"impossible","urgency":4,"travel_s":2,"feasible":False}]
    assert [x["id"] for x in rank_casualties(candidates)]==["critical","near"]


def test_route_search_failure_does_not_count_unvisited_area_as_surveyed(monkeypatch):
    import skyforge.planning as planning
    def route(start,goal,*args,**kwargs):
        if list(goal[:2])==[-12,-9]:return [list(start),[-12,-9,6]]
        return None
    monkeypatch.setattr(planning,'astar',route)
    planner=PlannerAgent({'reserve_wh':1})
    state={'position_enu_m':[0,0,8],'base_enu_m':[-12,-9,.05],'battery_wh':15,
           'snapshot_seq':1,'obstacle_circles':[],'events':[]}
    result=planner.plan(state,{})
    assert result['phase']=='EXPLORER'
    assert result['decision_code']=='COVERAGE_ROUTE_PENDING_HOLD'
    assert not planner.return_latched


def test_temporary_blocked_return_does_not_latch_full_battery_return():
    planner=PlannerAgent({"reserve_wh":1})
    state={"position_enu_m":[0,0,6],"base_enu_m":[-12,-9,.05],"battery_wh":15,
           "snapshot_seq":1,"obstacle_circles":[{"x":0,"y":0,"radius":2}],"events":[]}
    decision=planner.plan(state,{})
    assert not planner.return_latched
    assert decision["decision_code"]=="TEMPORARY_RETURN_ROUTE_BLOCKED_HOLD"


def test_station_objective_preempts_detected_casualty_and_honors_requested_altitude():
    planner=PlannerAgent({'reserve_wh':1});planner.phase='NAVIGUER'
    state={'position_enu_m':[-10,-8,8],'base_enu_m':[-12,-9,.05],'battery_wh':30,
           'snapshot_seq':2,'obstacle_circles':[],'events':[],'supply_count':3,
           'goal_revision':1,'goal_update':{'position':[-8,-8,6]}}
    casualty={'id':'casualty','class':'injured_person','position':[-9,-7,0],'seen_count':3,'last_seen':0}
    decision=planner.plan(state,{'casualty':casualty})
    assert decision['decision_code']=='GROUND_STATION_REROUTE'
    assert decision['waypoints_enu_m'][-1]==[-8.,-8.,6.]
    assert decision['request_delivery'] is None


def test_unsafe_station_objective_is_rejected_and_return_interrupt_has_priority():
    planner=PlannerAgent({'reserve_wh':1});planner.phase='NAVIGUER'
    state={'position_enu_m':[-10,-8,8],'base_enu_m':[-12,-9,.05],'battery_wh':30,
           'snapshot_seq':2,'obstacle_circles':[{'x':0,'y':0,'radius':2}],
           'events':[],'goal_revision':1,'goal_update':{'position':[0,0,6]}}
    decision=planner.plan(state,{})
    assert decision['decision_code']=='GROUND_OBJECTIVE_REJECTED_UNSAFE_OR_ENERGY'
    assert decision['waypoints_enu_m']==[state['position_enu_m']]
    assert planner.last_goal_revision==1
    state.update(battery_wh=.5,goal_revision=2)
    assert planner.plan(state,{})['phase']=='RETOUR_BASE'


def test_station_vertical_goal_does_not_reinsert_survey_altitude_during_descent():
    planner=PlannerAgent({'reserve_wh':1});planner.phase='NAVIGUER'
    state={'position_enu_m':[-7,-5,7.5],'base_enu_m':[-12,-9,.2],'battery_wh':20,
           'snapshot_seq':1,'obstacle_circles':[],'events':[],
           'goal_revision':1,'goal_update':{'position':[-7,-5,6]}}
    result=planner.plan(state,{})
    assert result['waypoints_enu_m']==[[-7.,-5.,7.5],[-7.,-5.,6.]]
