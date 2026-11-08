import socket
import threading
import msgpack
import pytest
from skyforge.airsim_rpc import AirSimRPC


def fake_server(response):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
    def serve():
        with listener:
            connection,_=listener.accept()
            with connection:
                unpacker=msgpack.Unpacker(raw=False)
                while True:
                    unpacker.feed(connection.recv(1024))
                    messages=list(unpacker)
                    if messages:break
                packed=msgpack.packb([1,messages[0][1],*response],use_bin_type=False)
                for i in range(0,len(packed),3):connection.sendall(packed[i:i+3])
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    return listener.getsockname()[1],thread


def test_fragmented_legacy_binary_response_preserves_png_bytes():
    png=b'\x89PNG\r\n\x1a\n\xff\x00\xc3\xa9'
    port,thread=fake_server((None,png))
    with AirSimRPC(port=port) as rpc:
        result=rpc.call('simGetImage','front_center',0,'SKYFORGE',False)
        assert result.encode('utf-8','surrogateescape')==png
    thread.join(2)


def test_remote_error_closes_connection_without_repeating_command():
    port,thread=fake_server(('simulated failure',None))
    with AirSimRPC(port=port) as rpc:
        with pytest.raises(RuntimeError,match='simulated failure'):rpc.call('takeoff',3,'SKYFORGE')
        assert rpc.socket is None
    thread.join(2)
