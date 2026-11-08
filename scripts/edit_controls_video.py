"""Caption the actual station objective/blackout demonstration."""
from pathlib import Path
import subprocess
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]
captions=[('Map objective / safe point - checked route - automatic flight',0,22),
          ('20 s radio blackout / autonomy continues - events buffer and replay',22,43),
          ('New map objective / safety and return reserve retain priority',43,70)]
filters=[]
for i,(caption,start,end) in enumerate(captions):
    p=ROOT/'artifacts'/f'controls-caption-{i}.txt';p.write_text(caption,encoding='utf-8')
    escaped=p.as_posix().replace(':',r'\:')
    filters.append(f"drawbox=x=0:y=80:w=1600:h=65:color=0x0b1116@0.90:t=fill:enable='between(t,{start},{end})'")
    filters.append(f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{escaped}':fontsize=27:fontcolor=white:x=30:y=96:enable='between(t,{start},{end})'")
filters.append('setpts=PTS/2')
out=ROOT/'deliverables/SKYFORGE-controls-32s.mp4'
source=ROOT/'deliverables/SKYFORGE-controls-full-mission.mp4'
if not source.exists():source=ROOT/'artifacts/SKYFORGE-controls-recording/full-mission.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-i',str(source),'-vf',','.join(filters),'-an','-c:v','libx264','-threads','1','-preset','fast','-crf','22',str(out)],check=True)
print(out)
