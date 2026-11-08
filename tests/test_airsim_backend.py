import numpy as np
import pytest
from skyforge.airsim_backend import NED_TO_ENU,body_quaternion_enu_flu,AirSimBackend
from skyforge.geometry import rotation_xyzw


def test_ned_and_body_axes_convert_to_enu_without_reflection():
    rotation=rotation_xyzw(body_quaternion_enu_flu([0,0,0,1]))
    np.testing.assert_allclose(rotation[:,0],[0,1,0],atol=1e-12)
    np.testing.assert_allclose(rotation[:,1],[-1,0,0],atol=1e-12)
    assert np.linalg.det(rotation)==pytest.approx(1)
    np.testing.assert_allclose(NED_TO_ENU@np.array([2,3,-4]),[3,2,4])


class RPC:
    def __init__(self,**kwargs):self.calls=[]
    def call(self,method,*args):self.calls.append((method,args));return True
    def close(self):pass


def test_commands_require_enable_and_use_ned_vertical_sign():
    backend=AirSimBackend(rpc_factory=RPC)
    with pytest.raises(RuntimeError):backend.velocity([1,0,0])
    backend.control_enabled=True;backend.velocity([.3,.2,.5])
    method,args=backend.commands.calls[-1]
    assert method=='moveByVelocity'
    np.testing.assert_allclose(args[:3],[.2,.3,-.5])
    with pytest.raises(ValueError):backend.velocity([0,0,float('nan')])
    with pytest.raises(ValueError):backend.velocity([3,0,0])


def test_read_only_images_negotiate_cosys_signature_once():
    backend=AirSimBackend(rpc_factory=RPC)
    calls=[]
    def call(method,*args):
        calls.append((method,args))
        if len(args)==3:raise RuntimeError('Function was called with an invalid number of arguments')
        return ['frame']
    backend.camera.call=call
    assert backend.images([])==['frame']
    assert backend.images([])==['frame']
    assert [len(args) for _,args in calls]==[3,2,2]


def test_camera_uses_time_aligned_control_odometry_without_extra_navigation_calls():
    import cv2
    backend=AirSimBackend(rpc_factory=RPC)
    png=cv2.imencode('.png',np.zeros((3,3,3),np.uint8))[1].tobytes()
    backend.images=lambda _: [{'time_stamp':1_000_000_000,'image_data_uint8':png},
        {'time_stamp':1_000_000_000,'width':3,'height':3,'image_data_float':[8.]*9}]
    poses=[{'t':t,'t_ns':int(t*1e9),'p':np.array([t-.98,0.,8.]),'v':np.array([1.,0.,0.]),'q':np.array([0.,0.,0.,1.])} for t in (.98,1.02)]
    frame=backend.frame(pose_provider=lambda:poses)
    np.testing.assert_allclose(frame['pose']['p'],[.02,0,8],atol=1e-8)
    assert not backend.navigation.calls
    with pytest.raises(ValueError,match='timestamp gap'):
        backend.frame(pose_provider=lambda:[{**poses[0],'t_ns':1}])
