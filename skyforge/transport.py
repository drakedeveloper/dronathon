"""Gazebo transport adapter; ground-truth annotation channels are opt-in."""
from collections import deque
import threading
import time
import subprocess
import numpy as np
from gz.transport13 import Node
from gz.msgs10.image_pb2 import Image
from gz.msgs10.odometry_pb2 import Odometry
from gz.msgs10.twist_pb2 import Twist
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.laserscan_pb2 import LaserScan
from gz.msgs10.vector3d_pb2 import Vector3d
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_wrench_pb2 import EntityWrench
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.annotated_axis_aligned_2d_box_v_pb2 import AnnotatedAxisAligned2DBox_V
from .geometry import rotation_xyzw


def stamp(msg):
    return msg.header.stamp.sec+msg.header.stamp.nsec*1e-9


class GazeboBus:
    def __init__(self,annotations=False,camera_enabled=True):
        self.node=Node(); self.lock=threading.Lock()
        self.rgb=None; self.depth=None; self.boxes=None; self.pose=None
        self.poses=deque(maxlen=250); self.seq=0; self.sim_time=0.; self.errors=[]
        self.scan=None;self.wind=np.zeros(3)
        if camera_enabled:
            self.node.subscribe(Image,"/skyforge/camera/image",self._image)
            self.node.subscribe(Image,"/skyforge/camera/depth_image",self._depth)
        self.node.subscribe(Odometry,"/model/x3/odometry",self._odom)
        self.node.subscribe(Clock,"/clock",self._clock)
        self.node.subscribe(LaserScan,"/skyforge/lidar",self._scan)
        self.node.subscribe(Vector3d,"/skyforge/wind",self._wind)
        if annotations:
            self.node.subscribe(AnnotatedAxisAligned2DBox_V,"/skyforge/labels",self._boxes)
        self.velocity=self.node.advertise("/X3/gazebo/command/twist",Twist)
        self.mover=self.node.advertise("/model/moving_obstacle/cmd_vel",Twist)
        self.wrench=self.node.advertise("/world/skyforge/wrench/persistent",EntityWrench)
        self.clear_wrench=self.node.advertise("/world/skyforge/wrench/clear",Entity)

    def _clock(self,msg):
        self.sim_time=msg.sim.sec+msg.sim.nsec*1e-9

    def _scan(self,msg):self.scan=msg
    def _wind(self,msg):self.wind=np.array([msg.x,msg.y,msg.z])

    def _image(self,msg):
        try:
            pixels=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.step)
            channels=msg.step//msg.width
            rgb=pixels[:,:msg.width*channels].reshape(msg.height,msg.width,channels)
            if channels not in (3,4): raise ValueError(f"Unsupported color channels {channels}")
            bgr=np.ascontiguousarray(rgb[:,:,:3][:,:,::-1])
            with self.lock:
                self.seq+=1
                self.rgb=(self.seq,stamp(msg),time.monotonic_ns(),bgr)
        except Exception as exc: self.errors.append(str(exc))

    def _depth(self,msg):
        try:
            depth=np.frombuffer(msg.data,np.float32).reshape(msg.height,msg.step//4)[:,:msg.width].copy()
            with self.lock: self.depth=(stamp(msg),depth)
        except Exception as exc: self.errors.append(str(exc))

    def _boxes(self,msg):
        with self.lock: self.boxes=msg

    def _odom(self,msg):
        p=msg.pose.position; q=msg.pose.orientation
        current={"t":stamp(msg),"wall_ns":time.monotonic_ns(),"p":np.array([p.x,p.y,p.z]),
                 "q":np.array([q.x,q.y,q.z,q.w]),"v":np.zeros(3)}
        with self.lock:
            if self.pose:
                dt=current["t"]-self.pose["t"]
                if 0<dt<0.5: current["v"]=(current["p"]-self.pose["p"])/dt
            self.pose=current; self.poses.append(current)

    def frame(self):
        with self.lock:
            if self.rgb is None: return None
            seq,t,wall,bgr=self.rgb
            pose=min(self.poses,key=lambda p:abs(p["t"]-t)) if self.poses else None
            depth=self.depth[1] if self.depth and abs(self.depth[0]-t)<0.075 else None
            return {"frame_id":seq,"t":t,"wall_ns":wall,"image":bgr,"depth":depth,"pose":pose}

    def command(self,velocity_enu,yaw_rate=0.):
        pose=self.pose
        if pose is None: return
        local=rotation_xyzw(pose["q"]).T@np.asarray(velocity_enu,float)
        message=Twist(); message.linear.x,message.linear.y,message.linear.z=map(float,local)
        message.angular.z=float(yaw_rate); self.velocity.publish(message)

    def move_obstacle(self,velocity):
        message=Twist(); message.linear.x,message.linear.y,message.linear.z=map(float,velocity)
        self.mover.publish(message)

    def apply_force(self,force):
        entity=Entity(name="x3",type=Entity.MODEL)
        self.clear_wrench.publish(entity)
        message=EntityWrench(); message.entity.CopyFrom(entity)
        message.wrench.force.x,message.wrench.force.y,message.wrench.force.z=map(float,force)
        self.wrench.publish(message)

    def set_camera_pose(self,x,y,z):
        # Dataset generator only. Never use this to pilot the drone.
        message=Pose(name="dataset_camera")
        message.position.x=float(x); message.position.y=float(y); message.position.z=float(z)
        message.orientation.w=1.
        # The installed Python RPC binding times out despite discovery. The
        # official CLI works; use it only in the offline dataset process.
        request=f'name: "dataset_camera" position: {{x:{float(x)} y:{float(y)} z:{float(z)}}} orientation: {{w:1}}'
        result=subprocess.run(["gz","service","-s","/world/skyforge/set_pose","--reqtype","gz.msgs.Pose",
                               "--reptype","gz.msgs.Boolean","--timeout","3000","--req",request],
                              capture_output=True,text=True,timeout=5)
        return result.returncode==0 and "true" in result.stdout,result.stdout
