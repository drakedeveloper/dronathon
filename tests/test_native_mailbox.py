from skyforge.airsim_controller import NativeMailbox
from skyforge.comms import envelope
import pytest


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


@pytest.mark.parametrize('field,value',[('speed_limit','fast'),('speed_limit',2.),('phase','UNKNOWN'),
    ('available_wh',-1),('hold',1),('zones',[[0,0,-1]]),('valid_until',100000)])
def test_malformed_signed_controls_are_rejected_without_consuming_sequence(field,value):
    box=NativeMailbox(b'x'*32)
    data={'p':[0.,0.,8.],'valid_until':1000,'phase':'EXPLORER'}
    bad={**data,field:value}
    assert not box.receive(box.codec.encode(envelope('native','session','command',1,0,'setpoint',bad)))
    assert box.receive(box.codec.encode(envelope('native','session','command',1,0,'setpoint',data)))


def test_control_expiry_and_envelope_share_absolute_simulator_clock():
    box=NativeMailbox(b'x'*32);absolute=1794107871.5
    data={'p':[0.,0.,8.],'valid_until':int((absolute+.65)*1000),'phase':'EXPLORER'}
    assert box.receive(box.codec.encode(envelope('native','session','command',1,absolute,'setpoint',data)))
    assert box.reason(absolute+.1)=='OK'
