"""Local authenticated radio link with durable event replay and idempotent ACKs."""
from collections import deque
import json
import os
from pathlib import Path
import socket
import threading
import time
import uuid
from .security import Codec,PacketError,ReplayGuard,SequenceGap,checked_vector,flip_one_bit


def clean(value):
    """JSON-facing diagnostics use null for unknown/unbounded values."""
    import math
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if hasattr(value,"tolist"):return clean(value.tolist())
    return value


def load_key(path="/opt/skyforge/radio.key"):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:f.write(os.urandom(32))
    return p.read_bytes()


def envelope(mission,session,stream,seq,t,kind,data):
    return {"v":1,"mission":mission,"session":session,"stream":stream,"seq":seq,
            "t_sim_ms":max(0,int(t*1000)),"type":kind,"data":clean(data)}


class RadioClient:
    def __init__(self,mission,journal_dir,host="127.0.0.1",port=8765,key=None):
        self.mission=mission;self.session=uuid.uuid4().hex[:12];self.codec=Codec(load_key() if key is None else key)
        self.host=host;self.port=port;self.events=deque(maxlen=4096);self.lock=threading.Lock()
        self.event_seq=0;self.status_seq=0;self.ack_seq=0;self.last_ack=0;self.connected=False
        self.latest={};self.t=0.;self.commands=deque(maxlen=64);self.guard=ReplayGuard()
        self.counters={"crc_rejected":0,"auth_rejected":0,"replay_rejected":0,"overflows":0,"reconnects":0}
        folder=Path(journal_dir);folder.mkdir(parents=True,exist_ok=True)
        self.journal=(folder/f"radio-{self.session}.jsonl").open("ab",buffering=0)
        self.stop=threading.Event();self.worker=threading.Thread(target=self._run,daemon=True);self.worker.start()

    def publish_status(self,data,t):self.latest=clean(data);self.t=t

    def event(self,kind,data,t):
        with self.lock:
            if len(self.events)==self.events.maxlen:
                self.counters["overflows"]+=1
                raise BufferError("Declared durable-event capacity exhausted")
            self.event_seq+=1
            body=envelope(self.mission,self.session,"event",self.event_seq,t,kind,data)
            packet=self.codec.encode(body)
            self.events.append((self.event_seq,packet));self.journal.write(packet)

    def pop_commands(self):
        result=[]
        while self.commands:result.append(self.commands.popleft())
        return result

    def _run(self):
        while not self.stop.is_set():
            try:
                with socket.create_connection((self.host,self.port),timeout=1) as sock:
                    sock.settimeout(.15);self.connected=True;self.counters["reconnects"]+=1
                    buffer=b"";last_send=0.;last_event_send=0.
                    while not self.stop.is_set():
                        now=time.monotonic()
                        if now-last_send>.2:
                            self.status_seq+=1
                            status=envelope(self.mission,self.session,"status",self.status_seq,self.t,"status",self.latest)
                            sock.sendall(self.codec.encode(status));last_send=now
                        if now-last_event_send>.5:
                            with self.lock:packets=list(self.events)[:32]
                            for _,packet in packets:sock.sendall(packet)
                            last_event_send=now
                        try:data=sock.recv(4096)
                        except socket.timeout:continue
                        if not data:raise ConnectionError("radio disconnected")
                        buffer+=data
                        if len(buffer)>64_000:raise PacketError("Unbounded receive buffer")
                        while b"\n" in buffer:
                            raw,buffer=buffer.split(b"\n",1)
                            try:
                                body=self.codec.decode(raw+b"\n")
                                if body["mission"]!=self.mission:raise PacketError("Wrong mission")
                                if body["type"]=="ack_events":
                                    upto=body["data"].get("up_to",0)
                                    if type(upto) is not int or not self.last_ack<=upto<=self.event_seq:raise PacketError("Invalid ACK")
                                    with self.lock:
                                        while self.events and self.events[0][0]<=upto:self.events.popleft()
                                        self.last_ack=upto
                                elif body["stream"]=="command":
                                    accepted=self.guard.accept(body)
                                    if accepted:
                                        if body["type"]=="goal_update":checked_vector(body["data"].get("position"),3,30)
                                        elif body["type"] not in ("state_bitflip",):raise PacketError("Unsupported command")
                                        self.commands.append(body)
                                    else:self.counters["replay_rejected"]+=1
                                    self.ack_seq+=1
                                    ack=envelope(self.mission,self.session,"ack",self.ack_seq,self.t,"ack_command",{"command_seq":body["seq"],"station_session":body["session"]})
                                    sock.sendall(self.codec.encode(ack))
                            except PacketError as exc:
                                key="crc_rejected" if "CRC" in str(exc) else "auth_rejected"
                                self.counters[key]+=1
            except (OSError,PacketError,ValueError):
                self.connected=False;self.stop.wait(.5)
        self.connected=False

    def close(self):
        self.stop.set();self.worker.join(timeout=3);self.journal.close()


class StationRadio:
    def __init__(self,port=8765,key=None):
        self.codec=Codec(load_key() if key is None else key);self.guard=ReplayGuard();self.session=uuid.uuid4().hex[:12]
        self.port=port;self.latest={};self.history=deque(maxlen=200);self.last_rx=0.;self.connected=False
        self.pending={};self.command_seq=0;self.ack_seq=0;self.mission=None;self.client_session=None
        self.blackout_until=0.;self.corrupt_next=False;self.last_command=None;self.replay_next=False
        self.lock=threading.Lock();self.stop=threading.Event();self.rejected=0;self.received_events=0
        self.ready=threading.Event()
        self.worker=threading.Thread(target=self._serve,daemon=True);self.worker.start()
        if not self.ready.wait(3):raise RuntimeError("Station radio listener did not start")

    def queue_command(self,kind,data):
        if self.mission is None:raise ValueError("Wait for the drone radio link")
        with self.lock:
            self.command_seq+=1
            body=envelope(self.mission,self.session,"command",self.command_seq,self.latest.get("t",0),kind,data)
            packet=self.codec.encode(body);self.pending[self.command_seq]=packet;self.last_command=packet
            return self.command_seq

    def _serve(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(("127.0.0.1",self.port));listener.listen(4);listener.settimeout(.5)
            self.port=listener.getsockname()[1];self.ready.set()
            while not self.stop.is_set():
                try:connection,_=listener.accept()
                except socket.timeout:continue
                with connection:
                    if time.monotonic()<self.blackout_until:continue
                    connection.settimeout(.1);buffer=b"";last_command_send=0.
                    try:
                        while not self.stop.is_set():
                            if time.monotonic()<self.blackout_until:break
                            if time.monotonic()-last_command_send>.5:
                                with self.lock:pending=list(self.pending.values())
                                for packet in pending:
                                    if self.corrupt_next:
                                        packet=flip_one_bit(packet,len(packet)//2,0);self.corrupt_next=False
                                    connection.sendall(packet)
                                if self.replay_next and self.last_command:
                                    connection.sendall(self.last_command);self.replay_next=False
                                last_command_send=time.monotonic()
                            try:data=connection.recv(4096)
                            except socket.timeout:continue
                            if not data:break
                            buffer+=data
                            if len(buffer)>64_000:raise PacketError("Unbounded radio buffer")
                            while b"\n" in buffer:
                                raw,buffer=buffer.split(b"\n",1)
                                try:
                                    body=self.codec.decode(raw+b"\n")
                                    self.mission=body["mission"];self.client_session=body["session"]
                                    self.last_rx=time.monotonic();self.connected=True
                                    if body["stream"]=="status":
                                        if self.guard.accept(body):self.latest=body["data"]
                                    elif body["stream"]=="event":
                                        try:accepted=self.guard.accept(body)
                                        except SequenceGap:accepted=False
                                        if accepted:self.history.append(body);self.received_events+=1
                                        key=(body["mission"],body["session"],"event")
                                        self.ack_seq+=1
                                        ack=envelope(body["mission"],self.session,"ack",self.ack_seq,0,"ack_events",{"up_to":self.guard.last.get(key,0)})
                                        connection.sendall(self.codec.encode(ack))
                                    elif body["type"]=="ack_command":
                                        if body["data"].get("station_session")==self.session:
                                            with self.lock:self.pending.pop(body["data"].get("command_seq"),None)
                                except PacketError:self.rejected+=1
                    except (OSError,PacketError):pass
                    self.connected=False

    def close(self):self.stop.set();self.worker.join(timeout=2)
