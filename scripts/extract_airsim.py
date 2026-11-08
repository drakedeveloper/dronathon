"""CRC-check and safely extract the official Windows scene onto D:."""
from pathlib import Path
import json
import shutil
import sys
import zipfile

archive=Path(sys.argv[1]).resolve();destination=archive.parent/'Coastline'
with zipfile.ZipFile(archive) as z:
    total=sum(i.file_size for i in z.infolist())
    if shutil.disk_usage(archive.parent).free < total+1024**3:
        raise OSError(f'Need {total/1024**3+1:.1f} GiB free for extraction and reserve')
    for item in z.infolist():
        if not (destination/item.filename).resolve().is_relative_to(destination.resolve()):
            raise ValueError('Archive path escapes scene folder')
    bad=z.testzip()
    if bad:raise ValueError('Archive CRC failure: '+bad)
    destination.mkdir(parents=True,exist_ok=True)
    z.extractall(destination)
exes=[str(p.relative_to(destination)) for p in destination.rglob('*.exe') if 'Prereq' not in p.name and 'CrashReport' not in p.name]
(archive.parent/'scene-manifest.json').write_text(json.dumps({'scene':'Coastline','uncompressed_bytes':total,'executables':exes},indent=2))
print(f'Coastline extracted and CRC-checked: {total/1024**3:.2f} GiB; executables: {exes}')
