from skyforge.evaluation import evaluate_trace


def scenario():
    return {'base':[-4,0,0], 'entities':[{'id':'hazard','class':'mine','position':[0,0,0]}],
            'obstacles':[{'center':[0,5,2],'size':[1,1,4]}]}


def test_fast_trace_cannot_tunnel_through_hazard_between_samples():
    trace=[{'p':[-4,0,6],'t':0},{'p':[4,0,6],'t':1}]
    report=evaluate_trace(trace,scenario())
    assert report['zone_entries']['hazard']==1
    assert report['minimum_hazard_center_distance_m']['hazard']==0


def test_airborne_final_position_is_not_a_successful_return():
    report=evaluate_trace([{'p':[-4,0,6],'t':30,'energy':2}],scenario())
    assert not report['landed_at_base']


def test_swept_vehicle_envelope_detects_box_collision():
    trace=[{'p':[-4,5,2],'t':0},{'p':[4,5,2],'t':1}]
    report=evaluate_trace(trace,scenario())
    assert report['static_collision_segments']==1
