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
