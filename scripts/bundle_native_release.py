"""Archive only the cooked Windows runtime; exclude symbols and generated state."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
base=Path(os.environ['LOCALAPPDATA'])/'SKYFORGE'
source=base/'Packaged/Windows'
target=base/'skyforge-native-win64.zip'
if not (source/'SKYFORGE.exe').is_file():raise RuntimeError('Package and launch the native simulator first')
notices={
    'AirSim-LICENSE.txt':'https://raw.githubusercontent.com/Cosys-Lab/Cosys-AirSim/5.8-v3.5.0/LICENSE',
}
license_data={}
for name,url in notices.items():
    with urllib.request.urlopen(url,timeout=30) as response:license_data[name]=response.read()
records=[]
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.suffix.lower() in ('.pdb','.log','.dmp'):continue
        relative=path.relative_to(source)
        if any(part in ('Saved','Intermediate','DerivedDataCache') for part in relative.parts):continue
        archive.write(path,Path('Windows')/relative)
        records.append({'file':relative.as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest()})
    archive.write(ROOT/'THIRD_PARTY_NOTICES.md','THIRD_PARTY_NOTICES.md')
    for name,data in license_data.items():archive.writestr('licenses/'+name,data)
    archive.writestr('runtime-manifest.json',json.dumps(records,indent=2))
digest=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
target.with_suffix('.sha256').write_text(digest+'  '+target.name+'\n')
print(json.dumps({'file':str(target),'bytes':target.stat().st_size,'sha256':digest,'runtime_files':len(records)},indent=2))
