"""Alternate genuine synchronized views from the recorded 90-second cut."""
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'deliverables/SKYFORGE-pitch-90s.mp4'
if not source.exists():source=ROOT/'artifacts/demo-recording/base-90s.mp4'
destination=ROOT/'deliverables/SKYFORGE-pitch-edited.mp4'
segments=[(0,10,'external'),(10,19,'split'),(19,29,'onboard'),(29,40,'map'),
          (40,51,'split'),(51,61,'onboard'),(61,78,'external'),(78,90,'split')]
filters=['[0:v]split='+str(len(segments))+''.join(f'[s{i}]' for i in range(len(segments)))]
for i,(start,end,view) in enumerate(segments):
    filters.append(f'[s{i}]trim=start={start}:end={end},setpts=PTS-STARTPTS[t{i}]')
    if view=='split':filters.append(f'[t{i}]setsar=1[o{i}]');continue
    filters.append(f'[t{i}]split=2[v{i}][h{i}]')
    crop={'external':'crop=800:420:24:80,scale=1600:840,pad=1600:900:0:60:color=0x0b1116',
          'onboard':'crop=512:384:24:504,scale=1200:900,pad=1600:900:200:0:color=0x0b1116',
          'map':'crop=720:540:850:80,scale=1200:900,pad=1600:900:200:0:color=0x0b1116'}[view]
    filters.append(f'[v{i}]{crop},setsar=1[b{i}]')
    filters.append(f'[h{i}]crop=1600:80:0:0[header{i}]')
    filters.append(f'[b{i}][header{i}]overlay=0:0:shortest=1[o{i}]')
filters.append(''.join(f'[o{i}]' for i in range(len(segments)))+f'concat=n={len(segments)}:v=1:a=0,format=yuv420p[out]')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-i',str(source),
    '-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264',
    '-threads','1','-preset','fast','-crf','21',str(destination)],check=True)
print(destination)
