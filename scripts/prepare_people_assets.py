"""Reproducible CC0 clothed human import and static casualty pose conversion."""
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from scripts.fetch_scene_assets import request
from scripts.convert_scene_assets import convert

COMMIT='187182d3cf9f4c53621a5e56320d9351a47248f0'
BASE=f'https://raw.githubusercontent.com/bultodepapas/OpenRCsimulator/{COMMIT}/'
ROOT=Path(__file__).resolve().parents[1]/'sim/assets/rescue_people'


def main():
    ROOT.mkdir(parents=True,exist_ok=True);records=[]
    def get(remote,local):
        data=request(BASE+remote);target=ROOT/local;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        records.append({'path':local,'source':BASE+remote,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        return data
    body=get('app/assets/scenery/population/people/casual_shirt_standing.glb','casual_shirt_standing.glb')
    count=struct.unpack_from('<I',body,12)[0];document=json.loads(body[20:20+count]);offset=20+count
    count=struct.unpack_from('<I',body,offset)[0];(ROOT/'casual_shirt_standing.bin').write_bytes(body[offset+8:offset+8+count])
    document['buffers'][0]['uri']='casual_shirt_standing.bin'
    source=ROOT/'casual_shirt_standing.gltf';source.write_text(json.dumps(document))
    for item in document['images']:get('app/assets/scenery/population/people/'+item['uri'],item['uri'])
    for name in ('HUMAN_LICENSES.md','HUMAN_SOURCES.json'):get('assets/scenery/population/'+name,name)
    convert(source)
    lines=source.with_suffix('.obj').read_text().splitlines()
    vertices=np.array([[float(n) for n in line.split()[1:]] for line in lines if line.startswith('v ')])
    # Standing Z-up to a face-up static casualty; centre its length and put its
    # back on the ground. Pose conversion is dataset/scene authoring only.
    midpoint=(vertices[:,2].max()+vertices[:,2].min())/2;back=vertices[:,1].max()
    output=[]
    for line in lines:
        if line.startswith(('v ','vn ')):
            tag,*values=line.split();x,y,z=map(float,values)
            point=(x,z-midpoint,-y+back+.025) if tag=='v' else (x,z,-y)
            line=tag+' '+' '.join(f'{n:.7g}' for n in point)
        output.append(line)
    (ROOT/'injured_person_clothed.obj').write_text('\n'.join(output)+'\n')
    (ROOT/'download-record.json').write_text(json.dumps({'license':'CC0-derived; see HUMAN_LICENSES.md','commit':COMMIT,'files':records},indent=2))
    print('Prepared textured standing and prone clothed humans',flush=True)


if __name__=='__main__':main()
