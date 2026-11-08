"""Inject an authorized20-second simulated radio outage during a live mission.

The local diagnostic tap remains separate from the disconnected radio. Save
actual observations; an empty event ring is not evidence of buffered replay.
"""
import json
from pathlib import Path
import time
import urllib.request

URL='http://127.0.0.1:8766'
def state():
    with urllib.request.urlopen(URL+'/api/state',timeout=3) as response:return json.load(response)

initial=state()
if initial['onboard_stale']:raise RuntimeError('No live mission; refusing to fabricate outage evidence')
request=urllib.request.Request(URL+'/api/command',data=json.dumps({'action':'outage'}).encode(),
    headers={'Content-Type':'application/json','X-CSRF-Token':initial['csrf']},method='POST')
with urllib.request.urlopen(request,timeout=3) as response:json.load(response)
samples=[];start=time.monotonic()
while time.monotonic()-start<29:
    current=state();samples.append({'wall_s':time.monotonic()-start,'sim_s':current['onboard'].get('t'),
        'phase':current['onboard'].get('phase'),'stale':current['onboard_stale'],
        'radio_connected':current['radio']['connected'],'pending_events':current['onboard'].get('pending_events',0),
        'received_events':current['radio']['received_events']})
    time.sleep(.4)
peak=max(s['pending_events'] for s in samples);final=samples[-1]
report={'mission_id':initial['onboard'].get('mission_id'),'initial_sim_s':initial['onboard']['t'],
        'final_sim_s':final['sim_s'],'autonomy_advanced':final['sim_s']>initial['onboard']['t']+1,
        'disconnection_observed':any(not s['radio_connected'] for s in samples[:35]),
        'reconnected':final['radio_connected'],'pending_peak':peak,'pending_final':final['pending_events'],
        'buffered_event_evidence':peak>0 and final['pending_events']==0,'samples':samples}
path=Path(__file__).resolve().parents[1]/'artifacts/live-outage.json';path.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
