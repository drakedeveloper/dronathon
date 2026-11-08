from skyforge.airsim_controller import NativeMailbox
from skyforge.comms import envelope


def test_signed_setpoint_replay_and_expiry_are_checked():
    box=NativeMailbox(b'x'*32)
    packet=box.codec.encode(envelope('native','session','command',1,0,'setpoint',
        {'p':[0.,0.,8.],'valid_until':1000,'phase':'EXPLORER'}))
    assert box.receive(packet)
    assert box.reason(.5)=='OK'
    assert not box.receive(packet)
    assert box.reason(2)=='STALE_AI_HOLD'


def test_internal_post_verification_bitflip_triggers_crc_hold():
    box=NativeMailbox(b'x'*32)
    packet=box.codec.encode(envelope('native','session','command',1,0,'setpoint',
        {'p':[1.,2.,8.],'valid_until':1000,'phase':'EXPLORER','fault_inject':True}))
    assert box.receive(packet)
    assert box.reason(.5)=='STATE_CRC_HOLD'
