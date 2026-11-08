"""Check Gazebo physics, ROS transport and a rendered test camera.

This is a runtime smoke test, not the competition mission. It adapts the
Apache-2.0 Gazebo multicopter example saved in sim/smoke and uses one UAV.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

import rclpy
import cv2
import numpy as np
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "gazebo-smoke"
OUT.mkdir(parents=True, exist_ok=True)
tree = ET.parse(ROOT / "sim/smoke/multicopter-upstream.sdf")
world = tree.getroot().find("world")
for include in list(world.findall("include"))[1:]:
    world.remove(include)
# An independent fixed camera verifies GPU sensor rendering and ROS image data.
# The competition drone's camera will be attached/calibrated during integration.
camera = ET.fromstring('''<model name="smoke_camera"><static>true</static>
<pose>0 -6 3 0 0.2 1.5707963</pose><link name="camera_link">
<sensor name="camera" type="camera"><always_on>true</always_on><update_rate>20</update_rate>
<topic>/skyforge/smoke/image</topic><camera><horizontal_fov>1.2</horizontal_fov>
<image><width>320</width><height>240</height><format>R8G8B8</format></image>
<clip><near>0.1</near><far>100</far></clip></camera></sensor></link></model>''')
world.append(camera)
world_path = OUT / "multicopter-smoke.sdf"
tree.write(world_path, encoding="unicode")

processes = []
logs = []
positions = []
image_count = 0
first_image = None
result = {"purpose": "runtime smoke test only", "status": "failed"}


def launch(args, name):
    handle = (OUT / f"{name}.log").open("w")
    logs.append(handle)
    process = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    processes.append(process)
    return process


def on_odom(msg):
    p = msg.pose.pose.position
    positions.append([time.monotonic(), p.x, p.y, p.z])


def on_image(msg):
    global image_count, first_image
    image_count += 1
    if first_image is None:
        first_image = {"width": msg.width, "height": msg.height, "encoding": msg.encoding, "bytes": len(msg.data)}
        pixels = CvBridge().imgmsg_to_cv2(msg, desired_encoding="bgr8")
        first_image["mean_pixel"] = float(np.mean(pixels))
        first_image["std_pixel"] = float(np.std(pixels))
        cv2.imwrite(str(OUT / "camera.png"), pixels)


try:
    launch(["gz", "sim", "-s", "-r", "-v", "3", str(world_path)], "server")
    bridge_args = [
        "/model/x3/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        "/skyforge/smoke/image@sensor_msgs/msg/Image[gz.msgs.Image",
        "/X3/gazebo/command/twist@geometry_msgs/msg/Twist]gz.msgs.Twist",
    ]
    launch(["ros2", "run", "ros_gz_bridge", "parameter_bridge", *bridge_args], "bridge")
    rclpy.init()
    node = rclpy.create_node("skyforge_runtime_smoke")
    from rclpy.qos import qos_profile_sensor_data
    node.create_subscription(Odometry, "/model/x3/odometry", on_odom, qos_profile_sensor_data)
    node.create_subscription(Image, "/skyforge/smoke/image", on_image, qos_profile_sensor_data)
    pub = node.create_publisher(Twist, "/X3/gazebo/command/twist", 10)

    def run_for(seconds, x=0.0, z=0.0):
        deadline = time.monotonic() + seconds
        cmd = Twist()
        cmd.linear.x = x
        cmd.linear.z = z
        while time.monotonic() < deadline:
            pub.publish(cmd)
            rclpy.spin_once(node, timeout_sec=0.02)

    start = time.monotonic()
    while (not positions or image_count < 2) and time.monotonic() - start < 90:
        run_for(0.2)
        if processes[0].poll() is not None:
            raise RuntimeError("Gazebo exited; inspect server.log")
    if not positions or image_count < 2:
        raise RuntimeError(f"Missing pose/camera after startup: odom={len(positions)}, images={image_count}")
    assert first_image["mean_pixel"] > 0, "Rendered camera is black"
    before = positions[-1][1:]
    run_for(3, z=0.5)
    after_takeoff = positions[-1][1:]
    run_for(1)
    before_move = positions[-1][1:]
    run_for(3, x=0.4)
    after_move = positions[-1][1:]
    run_for(1)
    run_for(5, z=-0.4)
    after_descent = positions[-1][1:]
    result.update({"camera_frames": image_count, "first_image": first_image,
                   "odometry_samples": len(positions), "before": before,
                   "after_takeoff": after_takeoff, "before_move": before_move,
                   "after_move": after_move, "after_descent": after_descent})
    assert after_takeoff[2] - before[2] > 0.5, "Insufficient physical climb"
    assert abs(after_move[0] - before_move[0]) > 0.3, "Insufficient physical translation"
    assert after_descent[2] < after_takeoff[2], "Insufficient descent"
    result["status"] = "passed"
finally:
    (OUT / "result.json").write_text(json.dumps(result, indent=2))
    (OUT / "odometry.json").write_text(json.dumps(positions))
    if rclpy.ok():
        rclpy.shutdown()
    for process in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
    for handle in logs:
        handle.close()
    print(json.dumps(result, indent=2))
