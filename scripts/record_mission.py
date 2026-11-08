"""Record genuine camera frames and synchronized station telemetry to MP4.

The right-hand panel is a telemetry composition, not a browser screen capture.
Raw received snapshots are retained so every displayed value can be traced.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=420);parser.add_argument('--name',default='SKYFORGE');args=parser.parse_args()
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):raise ValueError('Invalid recording name')
    out=ROOT/'deliverables';out.mkdir(exist_ok=True)
    raw=ROOT/'artifacts'/('demo-recording' if args.name=='SKYFORGE' else args.name+'-recording');raw.mkdir(exist_ok=True)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();fps=5
    destination=out/(args.name+'-full-mission.mp4')
    video=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1600x900','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(destination)],stdin=subprocess.PIPE)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/consola.ttf',n)
    site=Image.open(ROOT/'station/dist/assets/mission-aerial.jpg').convert('RGB')
    last={};camera=None;observer=None;identity=None;start=time.monotonic();done=0;count=0
    def request(path):
        with urllib.request.urlopen('http://127.0.0.1:8768/'+path,timeout=1) as response:return response.read()
    try:
        with (raw/'snapshots.jsonl').open('w',encoding='utf-8') as journal:
            while time.monotonic()-start<args.seconds:
                tick=time.monotonic()
                try:
                    last=json.loads(request('api/state'));o=last['onboard']
                    if last['onboard_stale']:
                        if last.get('onboard',{}).get('phase')=='POSE':break
                        time.sleep(.2);continue
                    if identity is None:identity=o['mission_id']
                    if o.get('mission_id')!=identity:raise RuntimeError('Recording mission changed')
                    journal.write(json.dumps({'wall_s':tick-start,**last})+'\n')
                    camera=Image.open(io.BytesIO(request('camera.jpg'))).convert('RGB')
                    observer=Image.open(io.BytesIO(request('observer.jpg'))).convert('RGB')
                    camera.save(raw/f'camera-{count:05}.jpg',quality=90)
                    if count%5==0:observer.save(raw/f'observer-{count:05}.jpg',quality=90)
                except (OSError,ValueError,KeyError):
                    if not last:time.sleep(.2);continue
                o=last.get('onboard',{});frame=Image.new('RGB',(1600,900),'#0b1116');d=ImageDraw.Draw(frame)
                d.text((35,22),'SKYFORGE / AUTONOMOUS RESCUE',font=font(28),fill='#d4e9b5')
                d.text((1110,27),f"T+{o.get('t',0):06.1f}s  {o.get('phase','WAITING')}",font=font(22),fill='white')
                if observer:frame.paste(observer.resize((800,450)),(24,80))
                if camera:frame.paste(camera.resize((512,384)),(24,504))
                d.text((40,92),'ACTUAL SIMULATOR CAMERA',font=font(18),fill='white')
                d.text((40,518),'ACTUAL ONBOARD DETECTIONS',font=font(16),fill='white')
                terrain=site.crop((300,225,1300,975)).resize((720,540));frame.paste(terrain,(850,80));d=ImageDraw.Draw(frame,'RGBA')
                def xy(p):return (850+(p[0]+20)/40*720,80+(15-p[1])/30*540)
                for cell in o.get('coverage_cells',[]):
                    x,y=xy(cell);d.rectangle((x-4,y-4,x+4,y+4),fill=(75,180,140,45))
                for track in o.get('tracks',[]):
                    if track.get('invalidated'):continue
                    x,y=xy(track['position']);color='#f4bd6a' if track['class']=='injured_person' else '#f17875'
                    d.ellipse((x-5,y-5,x+5,y+5),fill=color)
                    if track['class'] in ('mine','weapon','hostile_unit'):d.ellipse((x-32,y-32,x+32,y+32),outline='#f17875',width=2)
                route=[xy(p) for p in o.get('route',[])]
                if len(route)>1:d.line(route,fill='#d4e9b5',width=3)
                if o.get('decision')=='GROUND_STATION_REROUTE' and route:
                    x,y=route[-1];d.ellipse((x-12,y-12,x+12,y+12),outline='white',width=3)
                    d.text((865,600),'NEW MAP OBJECTIVE / AUTHENTICATED',font=font(18),fill='white')
                if o.get('p'):
                    x,y=xy(o['p']);d.ellipse((x-8,y-8,x+8,y+8),fill='#a1e7ef')
                d.text((866,94),'SYNCHRONIZED STATION TELEMETRY',font=font(19),fill='white')
                lines=[f"Deliveries {o.get('served',0)} / 3",f"Energy {o.get('energy',0):.2f} Wh",f"Radio {'CONNECTED' if last.get('radio',{}).get('connected') else 'BLACKOUT / BUFFERING'}",f"Buffered events {o.get('pending_events',0)}",str(o.get('decision','')).replace('_',' ')]
                for i,line in enumerate(lines):d.text((860,644+i*35),line,font=font(21),fill='#dce7ed')
                explanation=o.get('explanation','');words=explanation.split();lines=[];line=''
                for word in words:
                    if len(line)+len(word)>24:lines.append(line);line=''
                    line+=word+' '
                lines.append(line)
                for i,line in enumerate(lines[:10]):d.text((558,550+i*27),line,font=font(17),fill='#9db2bb')
                # Preserve wall-clock duration even if an HTTP image read stalls.
                repeat=max(1,int((time.monotonic()-start)*fps)-count)
                payload=frame.tobytes()
                for _ in range(repeat):video.stdin.write(payload)
                count+=repeat
                if o.get('phase')=='POSE':
                    done+=1
                    if done>=15:break
                time.sleep(max(0,1/fps-(time.monotonic()-tick)))
    finally:
        video.stdin.close();video.wait(timeout=30)
    elapsed=count/fps
    # A labelled 90-second cut retains the complete sequence at constant speed.
    speed=max(1,elapsed/90)
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(destination),'-vf',f'setpts=PTS/{speed:.6f}','-an','-c:v','libx264','-threads','1','-preset','fast','-crf','22',str(out/(args.name+'-pitch-90s.mp4'))],check=True)
    (raw/'recording.json').write_text(json.dumps({'mission_id':identity,'frames':count,'fps':fps,'recorded_seconds':elapsed,'pitch_speed_multiplier':speed,'scope':'Actual simulator camera frames and timestamped station telemetry composition, not a browser screen recording'},indent=2))
    print(destination,flush=True)


if __name__=='__main__':main()
