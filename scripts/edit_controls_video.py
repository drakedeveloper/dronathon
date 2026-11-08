"""Use a readable two-panel layout for the genuine objective/radio recording."""
from pathlib import Path
import subprocess,imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]
captions=[('MAP OBJECTIVE / authenticated request - checked route - automatic flight',0,11),('20 s RADIO BLACKOUT / autonomy continues - events buffer and replay',11,21.5),('NEW OBJECTIVE / safety shield and return reserve keep priority',21.5,33)]
f=['[0:v]setpts=PTS/2,split=3[ext][map][data]', '[ext]crop=800:420:24:80,scale=1000:525,pad=1600:900:20:145:color=0x101b22[base]', '[map]crop=720:540:850:80,scale=540:405[m]', '[data]crop=720:220:850:636,scale=540:165[d]', '[base][m]overlay=1040:145[b]', '[b][d]overlay=1040:565[c]']
p=ROOT/'artifacts/controls-title.txt';p.write_text('SKYFORGE / OBJECTIVE AND RADIO CONTROLS')
esc=lambda p:p.as_posix().replace(':',r'\:')
tail=[f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{esc(p)}':fontsize=31:fontcolor=white:x=25:y=36"]
for i,(caption,start,end) in enumerate(captions):
    p=ROOT/'artifacts'/f'controls-caption-{i}.txt';p.write_text(caption)
    tail.append(f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{esc(p)}':fontsize=27:fontcolor=white:x=25:y=785:enable='between(t,{start},{end})'")
p=ROOT/'artifacts/controls-note.txt';p.write_text('Actual simulator camera + recorded station telemetry / 2x replay')
tail.append(f"drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':textfile='{esc(p)}':fontsize=21:fontcolor=0xa6b4bd:x=25:y=841")
f.append('[c]'+','.join(tail)+',format=yuv420p[out]')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-i',str(ROOT/'artifacts/SKYFORGE-controls-recording/full-mission.mp4'),'-filter_complex_threads','1','-filter_complex',';'.join(f),'-map','[out]','-an','-c:v','libx264','-threads','1','-preset','fast','-crf','20',str(ROOT/'deliverables/SKYFORGE-controls-32s.mp4')],check=True)
print('Two-panel controls clip saved.')
