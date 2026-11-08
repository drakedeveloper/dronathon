"""Small synchronous MessagePack-RPC client for the official AirSim binaries.

Avoids the legacy Tornado dependency in the old AirSim Python package. One
connection per calling thread, bounded response size and explicit timeouts.
This API has no authentication: bind the simulator to loopback only.
"""
import socket
import threading
import time
import msgpack


class AirSimRPC:
    def __init__(self,host='127.0.0.1',port=41451,timeout=5.):
        if host not in ('127.0.0.1','localhost'):
            raise ValueError('This adapter is restricted to a same-host simulator')
        self.address=(host,port);self.timeout=timeout;self.socket=None
        self.sequence=0;self.lock=threading.Lock();self.unpacker=None

    def close(self):
        if self.socket:
            self.socket.close();self.socket=None

    def call(self,method,*args,on_sent=None):
        with self.lock:
            try:
                if self.socket is None:
                    self.socket=socket.create_connection(self.address,self.timeout)
                    self.socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                    self.socket.settimeout(self.timeout)
                    self.unpacker=msgpack.Unpacker(raw=False,unicode_errors='surrogateescape',max_buffer_size=32*1024*1024,strict_map_key=False)
                self.sequence+=1;identity=self.sequence
                deadline=time.monotonic()+self.timeout
                self.socket.sendall(msgpack.packb([0,identity,method,list(args)],use_bin_type=True))
                if on_sent is not None:on_sent(time.monotonic_ns())
                while True:
                    for reply in self.unpacker:
                        if not isinstance(reply,list) or len(reply)!=4 or reply[0]!=1 or reply[1]!=identity:
                            raise ValueError('Unexpected RPC response')
                        if reply[2] is not None:raise RuntimeError(f'AirSim {method}: {reply[2]}')
                        return reply[3]
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise TimeoutError('Simulator RPC deadline exceeded')
                    self.socket.settimeout(remaining)
                    chunk=self.socket.recv(65536)
                    if not chunk:raise ConnectionError('Simulator closed RPC connection')
                    self.unpacker.feed(chunk)
            except Exception:
                # Never retry motion commands implicitly: a timeout may happen
                # after the simulator has already accepted a command.
                self.close();raise

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
