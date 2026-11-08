import json
from station.state import read_onboard


def test_missing_snapshot_is_stale_instead_of_crashing_http(tmp_path):
    data,stale=read_onboard(tmp_path/'missing.json')
    assert data['phase']=='WAITING' and stale


def test_snapshot_data_and_metadata_use_the_same_open_file(tmp_path,monkeypatch):
    p=tmp_path/'onboard.json';p.write_text(json.dumps({'phase':'NAVIGUER','t':12}))
    # A separate path.stat would race with atomic replacement on DrvFS.
    monkeypatch.setattr(type(p),'stat',lambda *_args,**_kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    data,stale=read_onboard(p)
    assert data['t']==12 and not stale
