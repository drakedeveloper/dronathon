"""Bounded authenticated radio messages, corruption detection and replay checks."""
import hashlib
import hmac
import json
import math
import zlib


class PacketError(ValueError):pass
class SequenceGap(PacketError):pass


def canonical(value):
    return json.dumps(value,separators=(",",":"),sort_keys=True,allow_nan=False).encode("utf-8")


class Codec:
    def __init__(self,key):
        if not isinstance(key,bytes) or len(key)<32:raise ValueError("Use a >=256-bit shared key")
        self.key=key

    def encode(self,body):
        self._validate(body)
        data=canonical(body);crc=f"{zlib.crc32(data)&0xffffffff:08x}"
        mac=hmac.new(self.key,data+crc.encode(),hashlib.sha256).hexdigest()
        packet=canonical({"body":body,"crc":crc,"mac":mac})+b"\n"
        if len(packet)>999:raise PacketError("Packet exceeds 999-byte wire limit")
        return packet

    def decode(self,packet):
        if len(packet)>999:raise PacketError("Oversized packet")
        try:
            envelope=json.loads(packet,parse_constant=lambda _: (_ for _ in ()).throw(PacketError("Non-finite JSON")))
            if set(envelope)!={"body","crc","mac"}:raise PacketError("Invalid envelope")
            data=canonical(envelope["body"])
            crc=f"{zlib.crc32(data)&0xffffffff:08x}"
            if envelope["crc"]!=crc:raise PacketError("CRC_CORRUPTION")
            expected=hmac.new(self.key,data+crc.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(envelope["mac"],expected):raise PacketError("AUTHENTICATION_FAILED")
            self._validate(envelope["body"])
            return envelope["body"]
        except PacketError:raise
        except (ValueError,TypeError,KeyError,AttributeError) as exc:raise PacketError("Malformed packet") from exc

    @staticmethod
    def _validate(body):
        if not isinstance(body,dict) or set(body)!={"v","mission","session","stream","seq","t_sim_ms","type","data"}:
            raise PacketError("Invalid message shape")
        if body["v"]!=1:raise PacketError("Unsupported protocol version")
        for key in ("seq","t_sim_ms"):
            if type(body[key]) is not int or body[key]<0:raise PacketError("Invalid counter/timestamp")
        for key in ("mission","session","type"):
            if not isinstance(body[key],str) or not 0<len(body[key])<=64:raise PacketError("Invalid identifier")
        if body["stream"] not in ("event","status","command","ack"):raise PacketError("Unknown stream")
        if not isinstance(body["data"],dict):raise PacketError("Invalid message data")
        canonical(body)


class ReplayGuard:
    def __init__(self):self.last={}
    def accept(self,body):
        key=(body["mission"],body["session"],body["stream"])
        old=self.last.get(key,0);seq=body["seq"]
        if seq<=old:return False
        if body["stream"]=="event" and seq!=old+1:raise SequenceGap(f"Expected event {old+1}")
        self.last[key]=seq
        return True


def flip_one_bit(packet,index=10,bit=0):
    if not 0<=index<len(packet) or not 0<=bit<8:raise ValueError("Invalid injection location")
    altered=bytearray(packet);altered[index]^=1<<bit;return bytes(altered)


def checked_vector(value,length,limit):
    if not isinstance(value,(list,tuple)) or len(value)!=length:raise PacketError("Invalid vector length")
    if any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>limit for v in value):
        raise PacketError("Non-finite or implausible vector")
    return value
