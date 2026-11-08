import json
from scripts.evaluate_native_mission import evaluate


def test_virtual_events_at_empty_ground_do_not_count_as_rescues(tmp_path):
    (tmp_path/'radio').mkdir()
    trace=[{'t':1.,'p':[-12,-9,2.2],'energy':10,'phase':'LIVRER'},
           {'t':2.,'p':[-12,-9,.2],'energy':9,'phase':'POSE'}]
    (tmp_path/'trace.json').write_text(json.dumps(trace))
    event={'body':{'type':'delivery_completed','t_sim_ms':1000,'data':{'target_track_id':'phantom'}}}
    (tmp_path/'radio'/'events.jsonl').write_text(json.dumps(event)+'\n')
    result=evaluate(tmp_path)
    assert result['virtual_delivery_events']==1
    assert result['unique_geometrically_valid_deliveries']==0
    assert result['returned_to_base']
    assert not result['all_three_rescued']


def test_contact_timestamps_are_retained_for_acceptance_review(tmp_path):
    (tmp_path/'radio').mkdir()
    trace=[{'t':0.,'p':[-12,-9,1.],'energy':20,'phase':'INIT','collision':{'has_collided':False}},
           {'t':1.,'p':[-12,-9,.2],'energy':19,'phase':'POSE','collision':{'has_collided':True,'time_stamp':123}}]
    (tmp_path/'trace.json').write_text(json.dumps(trace))
    result=evaluate(tmp_path)
    assert result['simulator_contact_timestamps']==[123]
    assert not result['safe_mission_geometric_pass']
