"""Verify imports, independent ROS publisher/subscriber and GPU prerequisites."""
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import cv2
import langgraph.graph
import numpy
import onnxruntime
import rclpy
from cv_bridge import CvBridge
from std_msgs.msg import String

result = {"python": sys.version, "executable": sys.executable,
          "numpy": numpy.__version__, "opencv": cv2.__version__,
          "langgraph": importlib.metadata.version("langgraph"),
          "onnxruntime": onnxruntime.__version__,
          "onnx_providers": onnxruntime.get_available_providers(),
          "cv_bridge": "import OK"}
image = numpy.zeros((4, 6, 3), dtype=numpy.uint8)
message = CvBridge().cv2_to_imgmsg(image, encoding="bgr8")
assert message.width == 6 and message.height == 4

rclpy.init()
publisher_node = rclpy.create_node("skyforge_check_publisher")
subscriber_node = rclpy.create_node("skyforge_check_subscriber")
received = []
subscriber_node.create_subscription(String, "/skyforge/check_env", lambda msg: received.append(msg.data), 10)
publisher = publisher_node.create_publisher(String, "/skyforge/check_env", 10)
deadline = time.monotonic() + 10
while time.monotonic() < deadline and len(received) < 3:
    publisher.publish(String(data="skyforge-check"))
    rclpy.spin_once(publisher_node, timeout_sec=0.02)
    rclpy.spin_once(subscriber_node, timeout_sec=0.05)
publisher_node.destroy_node()
subscriber_node.destroy_node()
rclpy.shutdown()
assert len(received) >= 3, "ROS DDS publish/subscribe failed"
result["ros_dds_messages_received"] = len(received)
result["status"] = "passed"
out = Path(__file__).resolve().parents[1] / "artifacts" / "wsl-environment.json"
out.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
