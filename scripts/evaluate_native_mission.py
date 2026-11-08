"""Independent geometric audit. Annotation truth is never imported by agents."""
import argparse
import json
import math
from pathlib import Path
from skyforge.scene import ROOT
from skyforge.evaluation import evaluate_trace


def evaluate(directory):
    if (directory/'trace.json').exists():trace=json.loads((directory/'trace.json').read_text())
    else:
        lines=(directory/'trace.jsonl').read_text().splitlines();trace=[]
        for index,line in enumerate(lines):
            try:trace.append(json.loads(line))
            except json.JSONDecodeError:
                if index<len(lines)-1:raise
    scene=json.loads((ROOT/'configs/scenes/coastal-rescue.json').read_text())
    people=[p for p in scene['simulator_and_evaluator_only']['entities'] if p['class']=='injured_person']
    events=[]
    for journal in (directory/'radio').glob('*.jsonl'):
        events.extend(json.loads(line)['body'] for line in journal.read_text().splitlines())
    deliveries=[];valid=set()
    for event in events:
        if event['type']!='delivery_completed':continue
        t=event['t_sim_ms']/1000
        pose=min(trace,key=lambda p:abs(p['t']-t))
        nearest=min(people,key=lambda person:math.dist(person['position'][:2],pose['p'][:2]))
        distance=math.dist(nearest['position'][:2],pose['p'][:2])
        accepted=distance<=1.5 and abs(pose['p'][2]-2.2)<=.4
        if accepted:valid.add(nearest['id'])
        deliveries.append({'t':t,'position_enu_m':pose['p'],'nearest_casualty':nearest['id'],
                           'horizontal_error_m':distance,'geometrically_valid':accepted})
    last=trace[-1] if trace else None
    geometry=evaluate_trace(trace,{'entities':scene['simulator_and_evaluator_only']['entities'],
        'obstacles':scene['simulator_and_evaluator_only']['obstacles'],'base':scene['mission']['base_enu_m']})
    contacts=sorted({int(p['collision']['time_stamp']) for p in trace if p.get('collision',{}).get('has_collided')
                     and p.get('collision',{}).get('time_stamp')})
    return {'mission_id':directory.name,'scope':'Independent geometric audit of virtual hover delivery; no physical release proof',
            'virtual_delivery_events':len(deliveries),'unique_geometrically_valid_deliveries':len(valid),
            'deliveries':deliveries,'last_sample':last,
            'returned_to_base':bool(last and last['phase']=='POSE' and math.dist(last['p'][:2],scene['mission']['base_enu_m'][:2])<.6),
            'all_three_rescued':len(valid)==3,'geometry':geometry,'simulator_contact_timestamps':contacts,
            'safe_mission_geometric_pass':bool(len(valid)==3 and geometry['landed_at_base'] and
                sum(geometry['zone_entries'].values())==0 and geometry['static_collision_segments']==0)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    report=evaluate(args.directory)
    (args.directory/'independent-evaluation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
