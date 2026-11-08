"""Read-only logical file-size audit; skip reparse points and system trees."""
from collections import defaultdict
import heapq
import json
import os
from pathlib import Path
import stat
import time

ROOT=Path(__file__).resolve().parents[1]
roots=[Path('C:/Games'),Path('C:/XboxGames'),Path('C:/Program Files'),Path('C:/Program Files (x86)'),
       Path('C:/Users'),Path('C:/ProgramData'),Path('D:/')]
totals=defaultdict(int);large=[];errors=0;count=0;start=time.monotonic()
for root in roots:
    if not root.exists():continue
    stack=[root];subtotal=0
    while stack:
        folder=stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        metadata=entry.stat(follow_symlinks=False)
                        if getattr(metadata,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name in ('$RECYCLE.BIN','System Volume Information','Recovery'):continue
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            size=metadata.st_size;count+=1;subtotal+=size
                            p=Path(entry.path);parts=p.parts
                            # Store directory buckets at several useful depths.
                            for depth in (2,3,4,5):
                                if len(parts)>depth:totals[str(Path(*parts[:depth]))]+=size
                            if size>=250*1024**2:
                                heapq.heappush(large,(size,entry.path))
                                if len(large)>80:heapq.heappop(large)
                    except OSError:errors+=1
        except OSError:errors+=1
    print(f'Scanned {root}: {subtotal/1024**3:.2f} GiB; {count} files total',flush=True)
report={'note':'Logical sizes, not allocated disk usage; hardlinks may be counted more than once. Reparse points, recycle bins, system recovery and inaccessible files excluded.',
        'seconds':time.monotonic()-start,'files':count,'inaccessible':errors,
        'folders':[{'path':p,'gib':round(n/1024**3,3)} for p,n in sorted(totals.items(),key=lambda x:-x[1]) if n>=500*1024**2],
        'large_files':[{'path':p,'gib':round(n/1024**3,3)} for n,p in sorted(large,reverse=True)]}
out=ROOT/'artifacts/storage-audit.json';out.write_text(json.dumps(report,indent=2))
print('Saved '+str(out),flush=True)
