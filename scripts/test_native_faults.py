"""Actual local native radio/state fault campaign; no fabricated samples."""
import json
from pathlib import Path
import time
import urllib.request

URL='http://127.0.0.1:8768'
def state():
    with urllib.request.urlopen(URL+'/api/state',timeout=4) as response:return json.load(response)
def command(action):
    snapshot=state()
    request=urllib.request.Request(URL+'/api/command',data=json.dumps({'action':action}).encode(),
        headers={'Content-Type':'application/json','X-CSRF-Token':snapshot['csrf']},method='POST')
    with urllib.request.urlopen(request,timeout=4) as response:return json.load(response)

initial=state()
if initial['onboard_stale'] or initial['onboard'].get('phase')=='POSE':raise RuntimeError('No active native mission')
mission=initial['onboard']['mission_id'];samples=[];start=time.monotonic()
command('outage');injected=set()
while time.monotonic()-start<38:
    elapsed=time.monotonic()-start;snapshot=state();onboard=snapshot['onboard']
    if snapshot['onboard_stale'] and onboard.get('mission_id') is None:
        time.sleep(.1);continue
    if onboard.get('mission_id')!=mission:raise RuntimeError('Mission changed during fault test')
    samples.append({'wall_s':elapsed,'sim_s':onboard.get('t'),'p':onboard.get('p'),
        'phase':onboard.get('phase'),'stale':snapshot['onboard_stale'],
        'radio':snapshot['radio'],'pending_events':onboard.get('pending_events'),
        'security':onboard.get('security',{}),'control':{k:onboard.get('control',{}).get(k) for k in ('reason','crc_hold_cycles','bad_packets')}})
    for deadline,action in [(23,'state_bitflip'),(26,'bitflip_packet'),(31,'replay')]:
        if elapsed>deadline and action not in injected and snapshot['radio']['connected']:
            command(action);injected.add(action)
    time.sleep(.25)
last=samples[-1];peak=max(s['pending_events'] or 0 for s in samples)
report={'mission_id':mission,'scope':'Live simulated faults; mission outcome is audited separately',
    'autonomy_advanced':last['sim_s']>initial['onboard']['t']+1,
    'outage_observed':any(not s['radio']['connected'] for s in samples[:60]),
    # A new checkpoint may be awaiting ACK at the last sample. Require an
    # actually observed drained backlog after reconnect, not an arbitrary
    # final instant with no newly generated events in flight.
    'events_buffered_and_replayed':peak>0 and any(s['wall_s']>20 and s['radio']['connected'] and s['pending_events']==0
        and s['radio']['received_events']>initial['radio']['received_events'] for s in samples),
    'state_crc_hold_observed':max(s['control'].get('crc_hold_cycles') or 0 for s in samples)>initial['onboard'].get('control',{}).get('crc_hold_cycles',0),
    'packet_corruption_rejected':sum(last['security'].get(k,0) for k in ('crc_rejected','auth_rejected'))>
        sum(initial['onboard'].get('security',{}).get(k,0) for k in ('crc_rejected','auth_rejected')),
    'replay_rejected':last['security'].get('replay_rejected',0)>initial['onboard'].get('security',{}).get('replay_rejected',0),
    'injected':sorted(injected),'samples':samples}
path=Path(__file__).resolve().parents[1]/'artifacts/native-faults.json';path.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
