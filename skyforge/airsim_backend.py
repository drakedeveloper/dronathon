"""Native AirSim sensor/control boundary with explicit NED/ENU/FRD/FLU frames.

No ROS/Gazebo imports. Camera, navigation and command connections are separate
so image transfer cannot monopolize the flight command socket. This boundary
does not itself run rescue agents or authorize payload delivery.
"""
from collections import deque
from pathlib import Path
import math
import time
import cv2
import numpy as np
from .airsim_rpc import AirSimRPC
from .geometry import rotation_xyzw

NED_TO_ENU=np.array([[0.,1,0],[1,0,0],[0,0,-1]])
FRD_TO_FLU=np.diag([1.,-1.,-1.])


def vector_xyz(data):
    values=np.array([data['x_val'],data['y_val'],data['z_val']],float)
    if not np.all(np.isfinite(values)):raise ValueError('Non-finite simulator vector')
    return values


def quaternion_xyzw(data):
    values=np.array([data['x_val'],data['y_val'],data['z_val'],data['w_val']],float)
    rotation_xyzw(values)
    return values/np.linalg.norm(values)


def body_quaternion_enu_flu(q_ned_frd):
    rotation=NED_TO_ENU@rotation_xyzw(q_ned_frd)@FRD_TO_FLU
    axis,_=cv2.Rodrigues(rotation);angle=float(np.linalg.norm(axis))
    if angle<1e-12:return np.array([0.,0,0,1])
    return np.r_[axis.ravel()/angle*math.sin(angle/2),math.cos(angle/2)]


def binary_data(data):
    if isinstance(data,str):return data.encode('utf-8','surrogateescape')
    return bytes(data)


class AirSimBackend:
    def __init__(self,vehicle='SKYFORGE',translation_enu=(0.,0.,0.),port=41451,rpc_factory=AirSimRPC):
        self.vehicle=vehicle;self.translation=np.asarray(translation_enu,float)
        if self.translation.shape!=(3,) or not np.all(np.isfinite(self.translation)):raise ValueError('Invalid simulator origin')
        self.navigation=rpc_factory(port=port,timeout=2)
        self.camera=rpc_factory(port=port,timeout=3)
        self.commands=rpc_factory(port=port,timeout=2)
        self.history=deque(maxlen=300);self.frame_id=0;self.control_enabled=False
        self.image_external_argument=True

    def state(self):
        raw=self.navigation.call('getMultirotorState',self.vehicle)
        k=raw['kinematics_estimated'];q=body_quaternion_enu_flu(quaternion_xyzw(k['orientation']))
        pose={'t':raw['timestamp']/1e9,'t_ns':int(raw['timestamp']),
              'p':NED_TO_ENU@vector_xyz(k['position'])+self.translation,
              'v':NED_TO_ENU@vector_xyz(k['linear_velocity']),'q':q,
              'collision':raw.get('collision',{}),'landed_state':raw.get('landed_state')}
        self.history.append(pose);return pose

    def enable_control(self):
        settings=self.commands.call('getSettingsString')
        import json
        if json.loads(settings).get('PhysicsEngineName')=='ExternalPhysicsEngine':
            raise RuntimeError('Spectator mode cannot be used for a physics mission')
        self.commands.call('enableApiControl',True,self.vehicle)
        if not self.commands.call('armDisarm',True,self.vehicle):raise RuntimeError('Simulator refused arming')
        self.control_enabled=True

    def velocity(self,enu_velocity,duration=.04,yaw_rate_deg_s=0.):
        values=np.asarray(enu_velocity,float)
        if values.shape!=(3,) or not np.all(np.isfinite(values)) or np.linalg.norm(values)>2.:
            raise ValueError('Velocity outside bounded simulation envelope')
        if not .02<=duration<=.25 or not math.isfinite(yaw_rate_deg_s) or abs(yaw_rate_deg_s)>45:
            raise ValueError('Invalid command duration/yaw rate')
        if not self.control_enabled:raise RuntimeError('Explicit control enable required')
        ned=NED_TO_ENU.T@values
        return self.commands.call('moveByVelocity',*map(float,ned),float(duration),0,
            {'is_rate':True,'yaw_or_rate':float(-yaw_rate_deg_s)},self.vehicle)

    def images(self,requests):
        # Cosys 3.5 exposes two arguments; classic AirSim also requires the
        # external-camera flag. Negotiate only this read-only call, never motion.
        if self.image_external_argument:
            try:return self.camera.call('simGetImages',requests,self.vehicle,False)
            except RuntimeError as error:
                if 'invalid number of arguments' not in str(error):raise
                self.image_external_argument=False
        return self.camera.call('simGetImages',requests,self.vehicle)

    def frame(self,pose_provider=None):
        before=self.state() if pose_provider is None else None
        requests=[{'camera_name':'downward','image_type':0,'pixels_as_float':False,'compress':True},
                  {'camera_name':'downward','image_type':1,'pixels_as_float':True,'compress':False}]
        requested=time.monotonic_ns()
        replies=self.images(requests)
        received=time.monotonic_ns();after=self.state() if pose_provider is None else None
        if len(replies)!=2:raise ValueError('Incomplete RGB/depth response')
        rgb,depth=replies
        image=cv2.imdecode(np.frombuffer(binary_data(rgb['image_data_uint8']),np.uint8),cv2.IMREAD_COLOR)
        if image is None:raise ValueError('Invalid simulator camera PNG')
        w,h=int(depth['width']),int(depth['height'])
        if not(1<=w<=2048 and 1<=h<=2048):raise ValueError('Invalid depth dimensions')
        values=np.asarray(depth['image_data_float'],np.float32)
        if values.size!=w*h:raise ValueError('Invalid depth payload length')
        values=values.reshape(h,w)
        if image.shape[:2]!=(h,w):values=cv2.resize(values,(image.shape[1],image.shape[0]),interpolation=cv2.INTER_NEAREST)
        rgb_ns=int(rgb['time_stamp']);depth_ns=int(depth['time_stamp'])
        if abs(rgb_ns-depth_ns)>75_000_000:raise ValueError('Unsynchronized RGB/depth')
        candidates=sorted(pose_provider() if pose_provider is not None else [before,after],key=lambda p:p['t_ns'])
        if not candidates:raise ValueError('No odometry available for camera frame')
        pose=min(candidates,key=lambda p:abs(p['t_ns']-rgb_ns))
        limit_ns=75_000_000 if pose_provider is not None else 150_000_000
        if abs(pose['t_ns']-rgb_ns)>limit_ns:raise ValueError('Camera/odometry timestamp gap')
        left=[p for p in candidates if p['t_ns']<=rgb_ns];right=[p for p in candidates if p['t_ns']>=rgb_ns]
        before=left[-1] if left else pose;after=right[0] if right else pose
        if after['t_ns']>before['t_ns'] and before['t_ns']<=rgb_ns<=after['t_ns']:
            fraction=(rgb_ns-before['t_ns'])/(after['t_ns']-before['t_ns'])
            q0,q1=before['q'],after['q']
            if q0@q1<0:q1=-q1
            q=(1-fraction)*q0+fraction*q1;q/=np.linalg.norm(q)
            pose={**pose,'p':before['p']*(1-fraction)+after['p']*fraction,'q':q,'t':rgb_ns/1e9,'t_ns':rgb_ns}
        elif pose_provider is not None:
            dt=(rgb_ns-pose['t_ns'])/1e9
            pose={**pose,'p':pose['p']+pose['v']*dt,'t':rgb_ns/1e9,'t_ns':rgb_ns}
        self.frame_id+=1
        return {'frame_id':self.frame_id,'t':rgb_ns/1e9,'wall_ns':received,'request_wall_ns':requested,
                'image':image,'depth':values,'pose':pose,'camera_id':'downward_rgb'}

    def lidar_points(self):
        raw=self.navigation.call('getLidarData','safety_lidar',self.vehicle)
        points=np.asarray(raw.get('point_cloud',[]),float)
        if points.size%3 or points.size>120000:raise ValueError('Invalid lidar point payload')
        points=points.reshape(-1,3)
        # Settings explicitly select VehicleInertialFrame (NED). Do not apply
        # this conversion to SensorLocalFrame data.
        return points@NED_TO_ENU.T+self.translation

    def close(self):
        if self.control_enabled:
            try:self.commands.call('moveByVelocity',0.,0.,0.,.05,0,{'is_rate':True,'yaw_or_rate':0.},self.vehicle)
            except (OSError,ValueError,RuntimeError):pass
        for rpc in (self.navigation,self.camera,self.commands):rpc.close()
