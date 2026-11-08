"""Read-only native Windows simulator connection and image inspection."""
import json
from pathlib import Path
import time
from skyforge.airsim_rpc import AirSimRPC

ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/airsim';out.mkdir(parents=True,exist_ok=True)
with AirSimRPC(timeout=8) as rpc:
    start=time.perf_counter();ping=rpc.call('ping')
    version=rpc.call('getServerVersion')
    state=rpc.call('getMultirotorState','SKYFORGE')
    image=rpc.call('simGetImage','front_center',0,'SKYFORGE',False)
    if isinstance(image,str):image=image.encode('utf-8','surrogateescape')
    if isinstance(image,list):image=bytes(image)
    if not image or len(image)<100:raise RuntimeError('No front camera image')
    (out/'front.png').write_bytes(image)
    result={'ping':ping,'server_version':version,'read_probe_ms':(time.perf_counter()-start)*1000,
            'timestamp':state['timestamp'],'collision':state.get('collision',{}),'image_bytes':len(image)}
    (out/'connection.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
