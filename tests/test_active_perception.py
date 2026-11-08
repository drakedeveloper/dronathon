import numpy as np
from skyforge.planning import PerceptionAgent
from skyforge.vision import ground_point_visible


def frame(identity=1):
    return {'image':np.zeros((384,512,3),np.uint8),'depth':np.full((384,512),7.88),
            'pose':{'p':np.array([0.,0.,8.]),'q':np.array([0.,0.,0.,1.])},'t':identity*.1}


def test_negative_evidence_requires_visible_unoccluded_ground():
    f=frame()
    assert ground_point_visible([0,0,0],f)
    assert not ground_point_visible([100,0,0],f)
    f['depth'][:]=3
    assert not ground_point_visible([0,0,0],f)


def test_repeated_empty_views_invalidate_phantom_but_not_out_of_view_target():
    agent=PerceptionAgent()
    for identity,position in [('phantom',[0,0,0]),('remote',[100,0,0])]:
        agent.tracks[identity]={'id':identity,'class':'injured_person','position':position,
                                'seen_count':3,'last_seen':0.,'confidence':.7}
    for identity in range(1,6):
        agent.update({'frame':frame(identity),'detections':{'frame_id':identity,'detections':[]}})
    assert agent.tracks['phantom']['invalidated']
    assert not agent.tracks['remote'].get('invalidated',False)
