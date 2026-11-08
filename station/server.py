"""Local-only ground station HTTP UI and independent authenticated radio receiver."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
from skyforge.comms import StationRadio,clean
from skyforge.physics import predict_payload_offset
from station.state import read_onboard

ROOT=Path(__file__).resolve().parents[1]
DIST=Path(__file__).resolve().parent/"dist"
LIVE=ROOT/"artifacts/live"
TOKEN=secrets.token_urlsafe(24)
PORT=int(os.environ.get('SKYFORGE_HTTP_PORT','8766'))
radio=StationRadio(port=int(os.environ.get('SKYFORGE_RADIO_PORT','8765')),state_path=ROOT/'artifacts/station'/f'radio-state-{PORT}.json')


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def respond(self,data,status=200,kind="application/json"):
        content=data if isinstance(data,bytes) else json.dumps(clean(data),allow_nan=False).encode()
        self.send_response(status);self.send_header("Content-Type",kind)
        self.send_header("Content-Length",str(len(content)));self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Frame-Options","DENY")
        self.end_headers();self.wfile.write(content)

    def do_GET(self):
        if self.headers.get("Host") not in (f"localhost:{PORT}",f"127.0.0.1:{PORT}"):
            return self.respond({"error":"host rejected"},403)
        path=urlsplit(self.path).path
        if path=="/api/state":
            onboard,stale=read_onboard(LIVE/'onboard.json')
            return self.respond({"csrf":TOKEN,"onboard":onboard,"onboard_stale":stale,"station":radio.latest,
                "radio":{"connected":radio.connected and time.monotonic()-radio.last_rx<2,
                         "pending_commands":len(radio.pending),"rejected":radio.rejected,
                         "received_events":radio.received_events,"blackout_seconds":max(0,radio.blackout_until-time.monotonic())},
                "events":list(radio.history)[-35:]})
        if path in ("/camera.jpg","/observer.jpg"):
            p=LIVE/path[1:]
            try:content=p.read_bytes()
            except FileNotFoundError:return self.respond(b"",404,kind="image/jpeg")
            return self.respond(content,kind="image/jpeg")
        if path=="/":return self.respond((DIST/"index.html").read_bytes(),kind="text/html; charset=utf-8")
        return self.respond({"error":"not found"},404)

    def do_POST(self):
        if self.headers.get("Host") not in (f"localhost:{PORT}",f"127.0.0.1:{PORT}"):
            return self.respond({"error":"host rejected"},403)
        origin=self.headers.get("Origin","")
        if origin and origin not in (f"http://localhost:{PORT}",f"http://127.0.0.1:{PORT}"):
            return self.respond({"error":"origin rejected"},403)
        if not secrets.compare_digest(self.headers.get("X-CSRF-Token",""),TOKEN):
            return self.respond({"error":"token rejected"},403)
        try:
            length=int(self.headers.get("Content-Length",0))
            if not 0<length<=2048:raise ValueError("invalid request size")
            data=json.loads(self.rfile.read(length));action=data.get("action")
            if action=="outage":radio.blackout_until=time.monotonic()+20
            elif action=="bitflip_packet":
                radio.corrupt_next=True;position=radio.latest.get("p",[-12,-9,6]);position=[*position[:2],6]
                radio.queue_command("goal_update",{"position":position,"revision":radio.command_seq+1})
            elif action=="replay":radio.replay_next=True
            elif action=="state_bitflip":radio.queue_command("state_bitflip",{"test":True})
            elif action=="goal":
                position=data["position"]
                if len(position)!=3 or not (-14<=position[0]<=14 and -11<=position[1]<=11 and .5<=position[2]<=8):
                    raise ValueError("goal outside safe envelope")
                radio.queue_command("goal_update",{"position":position,"revision":radio.command_seq+1})
            elif action=="drop_predict":
                offset,duration=predict_payload_offset(float(data.get("height",2.2)),data.get("wind",[1,0]))
                return self.respond({"offset_m":offset.tolist(),"fall_time_s":duration})
            else:raise ValueError("unknown action")
            return self.respond({"ok":True})
        except (ValueError,KeyError,TypeError) as exc:return self.respond({"error":str(exc)},400)


if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    print(f"SKYFORGE ground station: http://localhost:{PORT}",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:radio.close();server.server_close()
