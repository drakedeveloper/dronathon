"""Create clean, genuine camera footage with English captions and six chapters."""
import bisect,json,subprocess
from pathlib import Path
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables';RAW=ROOT/'artifacts/demo-recording'
CHAPTERS=[(0,10,'01-launch','Launch and initial climb'),(10,20,'02-exploration','Exploration and first observations'),(20,30,'03-detection','Visual confirmation and mapping'),(30,45,'04-navigation','Checked navigation and approach'),(45,63,'05-delivery','Target confirmation and virtual aid'),(63,90,'06-return','Return, descent and touchdown')]
ENGLISH={'INIT':'INITIALIZE','EXPLORER':'EXPLORE','DETECTER':'DETECT','TRIAGE':'TRIAGE','NAVIGUER':'NAVIGATE','LIVRER':'DELIVER','RETOUR_BASE':'RETURN TO BASE','POSE':'LANDED'}
def main():
    frames={k:sorted((int(p.stem.split('-')[-1]),p) for p in RAW.glob(k+'-*.jpg')) for k in ('camera','observer')}
    indices={k:[n for n,p in v] for k,v in frames.items()}
    records=[json.loads(x) for x in (RAW/'snapshots.jsonl').read_text().splitlines()];times=[r['wall_s'] for r in records]
    info=json.loads((RAW/'recording.json').read_text());speed=info.get('recorded_seconds',168.4)/90
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    process=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1600x900','-r','5','-i','-','-an','-c:v','libx264','-threads','1','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(OUT/'SKYFORGE-pitch-edited.mp4')],stdin=subprocess.PIPE)
    def recorded(kind,index):
        ns=indices[kind];j=min(bisect.bisect_left(ns,index),len(ns)-1)
        if j and abs(ns[j-1]-index)<abs(ns[j]-index):j-=1
        return Image.open(frames[kind][j][1]).convert('RGB')
    for number in range(450):
        t=number/5;wall=t*speed;o=records[min(bisect.bisect_left(times,wall),len(records)-1)]['onboard']
        onboard=18<=t<26 or 47<=t<58
        source=recorded('camera' if onboard else 'observer',round(wall*5));frame=Image.new('RGB',(1600,900),'#101b22')
        if onboard:
            view=ImageOps.contain(source,(1200,800),Image.Resampling.LANCZOS);frame.paste(view,((1600-view.width)//2,80+(800-view.height)//2))
        else:frame.paste(ImageOps.fit(source,(1600,900),Image.Resampling.LANCZOS),(0,0))
        d=ImageDraw.Draw(frame,'RGBA');d.rectangle((0,0,1600,80),fill=(13,25,32,235));d.text((30,17),'SKYFORGE',font=font(30),fill='#e5e9dc')
        d.text((320,23),ENGLISH.get(o.get('phase'),o.get('phase','WAITING')),font=font(23),fill='white')
        d.text((1110,23),f"T+{o.get('t',0):05.1f}s   {speed:.2f}x REPLAY",font=font(23),fill='#d9d4c8')
        d.rectangle((0,823,1600,900),fill=(13,25,32,235));d.text((30,840),'ONBOARD DETECTIONS' if onboard else 'EXTERNAL FLIGHT CAMERA',font=font(22),fill='white')
        d.text((650,840),f"VIRTUAL AID {o.get('served',0)}/3       ENERGY {o.get('energy',0):.2f} Wh",font=font(24),fill='#d5e4c5')
        if number in (25,110,260,415):frame.save(ROOT/'artifacts'/f'pitch-clean-{number}.jpg')
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    if process.wait()!=0:raise RuntimeError('Video encoder failed')
    for start,end,name,title in CHAPTERS:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(OUT/'SKYFORGE-pitch-edited.mp4'),'-t',str(end-start),'-an','-c:v','libx264','-threads','1','-preset','fast','-crf','20',str(OUT/(name+'.mp4'))],check=True)
    (OUT/'video-chapters.json').write_text(json.dumps({'speed':speed,'source_mission':info['mission_id'],'chapters':[{'file':n+'.mp4','title':title,'duration_s':end-start,'source_edit_start_s':start} for start,end,n,title in CHAPTERS]},indent=2))
    print('Clean 90-second edit and six chapter clips saved.')
if __name__=='__main__':main()
