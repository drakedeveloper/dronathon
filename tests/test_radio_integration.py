import time
from skyforge.comms import RadioClient,StationRadio


def until(predicate,seconds=5):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return True
        time.sleep(.03)
    return False


def test_real_socket_outage_replay_and_no_duplicate_events(tmp_path):
    key=b"test-radio-integrity-key-32bytes!!"
    station=StationRadio(port=0,key=key)
    client=RadioClient("integration",tmp_path,port=station.port,key=key)
    try:
        client.publish_status({"t":1,"phase":"EXPLORER"},1)
        assert until(lambda:station.connected)
        client.event("detected",{"target":"a"},1)
        assert until(lambda:client.last_ack==1)
        station.blackout_until=time.monotonic()+.8
        assert until(lambda:not client.connected)
        client.event("delivered",{"target":"a"},2)
        client.event("returned",{},3)
        assert until(lambda:client.last_ack==3,6)
        assert station.received_events==3
        assert len(client.events)==0
    finally:client.close();station.close()


def test_corrupt_command_is_rejected_then_clean_retry_applies_once(tmp_path):
    key=b"test-radio-integrity-key-32bytes!!"
    station=StationRadio(port=0,key=key);client=RadioClient("fault",tmp_path,port=station.port,key=key)
    try:
        client.publish_status({"t":1},1)
        assert until(lambda:station.connected)
        station.corrupt_next=True
        station.queue_command("goal_update",{"position":[1,2,6],"revision":1})
        assert until(lambda:len(client.commands)==1)
        assert client.counters["crc_rejected"]+client.counters["auth_rejected"]>=1
        assert until(lambda:not station.pending)
        station.replay_next=True
        assert until(lambda:client.counters["replay_rejected"]>=1)
        assert len(client.commands)==1
    finally:client.close();station.close()
