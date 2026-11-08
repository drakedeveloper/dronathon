import json
from station.state import read_evaluation


def test_report_from_another_mission_is_never_displayed_as_current(tmp_path):
    report=tmp_path/'report.json'
    report.write_text(json.dumps({'mission_id':'previous','all_three_rescued':True}))
    assert read_evaluation(report,'current') is None
    assert read_evaluation(report,'previous')['all_three_rescued']
