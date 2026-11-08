import json
import pytest
from skyforge.security import Codec,PacketError,ReplayGuard,SequenceGap,flip_one_bit,checked_vector


def message(seq=1,stream="event"):
    return {"v":1,"mission":"test","session":"boot1","stream":stream,"seq":seq,"t_sim_ms":1000,"type":"goal_update","data":{"position":[1,2,6]}}


def test_roundtrip_is_compact_and_authenticated():
    codec=Codec(b"a"*32);wire=codec.encode(message())
    assert len(wire)<1000 and codec.decode(wire)==message()
    with pytest.raises(PacketError):Codec(b"b"*32).decode(wire)


def test_each_single_bit_corruption_is_rejected():
    codec=Codec(b"a"*32);wire=codec.encode(message())
    for index in range(len(wire)-1):
        with pytest.raises(PacketError):codec.decode(flip_one_bit(wire,index,0))


def test_crc_repair_does_not_forge_authentication():
    import zlib
    from skyforge.security import canonical
    codec=Codec(b"a"*32);envelope=json.loads(codec.encode(message()))
    envelope["body"]["data"]["position"]=[12,12,6]
    envelope["crc"]=f'{zlib.crc32(canonical(envelope["body"]))&0xffffffff:08x}'
    with pytest.raises(PacketError,match="AUTHENTICATION_FAILED"):codec.decode(canonical(envelope))


def test_replay_and_gap_do_not_advance_receiver():
    guard=ReplayGuard();assert guard.accept(message())
    assert not guard.accept(message())
    with pytest.raises(SequenceGap):guard.accept(message(3))
    assert guard.accept(message(2));assert guard.accept(message(3))


def test_nonfinite_and_oversized_commands_fail_closed():
    codec=Codec(b"a"*32);bad=message();bad["data"]["x"]=float("nan")
    with pytest.raises((ValueError,PacketError)):codec.encode(bad)
    bad=message();bad["data"]["x"]="x"*1500
    with pytest.raises(PacketError):codec.encode(bad)
    with pytest.raises(PacketError):checked_vector([0,0,float("inf")],3,100)
