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
    f['depth'][:]=7.65
    assert not ground_point_visible([0,0,0],f)  # A prone person is not empty ground.


def test_repeated_empty_views_invalidate_phantom_but_not_out_of_view_target():
    agent=PerceptionAgent()
    for identity,position in [('phantom',[0,0,0]),('remote',[100,0,0])]:
        agent.tracks[identity]={'id':identity,'class':'injured_person','position':position,
                                'seen_count':3,'last_seen':0.,'confidence':.7}
    for identity in range(1,6):
        agent.update({'frame':frame(identity),'detections':{'frame_id':identity,'detections':[]}})
    assert agent.tracks['phantom']['invalidated']
    assert not agent.tracks['remote'].get('invalidated',False)


def test_brief_wrong_person_class_does_not_create_a_permanent_second_threat():
    agent=PerceptionAgent()
    for index,kind in enumerate(['injured_person']*4+['hostile_unit']+['injured_person']*4,1):
        f=frame(index)
        agent.update({'frame':f,'detections':{'frame_id':index,'detections':[
            {'class':kind,'confidence':.7,'bbox_xyxy':[250,185,262,197]}]}})
    assert len(agent.tracks)==1
    track=next(iter(agent.tracks.values()))
    assert track['class']=='injured_person'
    assert not track['classification_uncertain']
