from skyforge.airsim_mission import atomic_json


def test_windows_reader_lock_does_not_kill_flight_publication(tmp_path,monkeypatch):
    target=tmp_path/'onboard.json';target.write_text('{"phase":"INIT"}')
    def locked(*_):raise PermissionError('Windows reader holds target briefly')
    monkeypatch.setattr('skyforge.airsim_mission.os.replace',locked)
    monkeypatch.setattr('skyforge.airsim_mission.time.sleep',lambda _:None)
    assert atomic_json(target,{'phase':'EXPLORER'}) is False
    assert target.read_text()=='{"phase":"INIT"}'
