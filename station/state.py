"""Read one consistent onboard snapshot while the producer replaces its file."""
import json
import os
import time


def read_onboard(path):
    try:
        with path.open('r') as handle:
            stamp=os.fstat(handle.fileno()).st_mtime
            data=json.load(handle)
        return data,time.time()-stamp>3
    except (FileNotFoundError,PermissionError,json.JSONDecodeError):
        return {'phase':'WAITING','t':0},True


def read_evaluation(path,mission):
    try:
        report=json.loads(path.read_text())
        return report if report.get('mission_id')==mission else None
    except (FileNotFoundError,PermissionError,json.JSONDecodeError):return None
