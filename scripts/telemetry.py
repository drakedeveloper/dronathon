"""Read MAVLink heartbeat only. Never arms or sends flight commands."""
import argparse
import json
from pymavlink import mavutil

parser = argparse.ArgumentParser()
parser.add_argument("--connect", default="tcp:127.0.0.1:5760")
parser.add_argument("--timeout", type=float, default=20)
args = parser.parse_args()
link = mavutil.mavlink_connection(args.connect, source_system=255)
try:
    heartbeat = link.wait_heartbeat(timeout=args.timeout)
    if heartbeat is None:
        raise SystemExit("No heartbeat received before timeout")
    print(json.dumps({"system": link.target_system, "component": link.target_component,
                      "heartbeat": heartbeat.to_dict()}, indent=2))
finally:
    link.close()
