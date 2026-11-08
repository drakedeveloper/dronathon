import argparse
import json
from pathlib import Path
from skyforge.evaluation import evaluate_trace

parser=argparse.ArgumentParser();parser.add_argument('mission',type=Path);args=parser.parse_args()
scenario=json.loads((Path(__file__).resolve().parents[1]/'sim/generated/coast.json').read_text())
report=evaluate_trace(json.loads((args.mission/'trace.json').read_text()),scenario)
(args.mission/'evaluation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
