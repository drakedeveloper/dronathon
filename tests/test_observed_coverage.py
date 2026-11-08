import numpy as np
from skyforge.coverage import CoverageGrid


def frame(depth,identity=1):
    return {'frame_id':identity,'depth':depth,'pose':{'p':np.array([0.,0.,8.12]),'q':[0,0,0,1]}}


def test_only_visible_camera_footprint_is_counted_and_duplicates_do_not_add_hits():
    grid=CoverageGrid();f=frame(np.full((480,640),8.))
    grid.update(f);observed=grid.summary()['observed_cells'];hits=grid.hits.copy()
    assert 100<observed<600
    assert not grid.hits[0]
    grid.update(f);np.testing.assert_array_equal(hits,grid.hits)


def test_occluded_ground_is_not_falsely_certified_observed():
    grid=CoverageGrid();grid.update(frame(np.full((480,640),4.)))
    assert grid.summary()['observed_cells']==0


def test_invalid_depth_and_insufficient_resolution_remain_unknown():
    grid=CoverageGrid();grid.update(frame(np.full((480,640),np.nan)))
    assert grid.summary()['observed_cells']==0
    f=frame(np.full((480,640),50.),2);f['pose']['p'][2]=50.12
    grid.update(f);assert grid.summary()['observed_cells']==0
