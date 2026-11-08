"""Convert the selected single-mesh glTF assets to Gazebo-friendly textured OBJ.

Preserves UVs/normals, converts glTF Y-up to simulator Z-up. Rejects features
outside this deliberately small importer instead of silently dropping transforms.
"""
from pathlib import Path
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]/'sim/assets'


def convert(path):
    data=json.loads(path.read_text())
    nodes=data['nodes']
    if len(nodes)!=1 or any(k in nodes[0] for k in ('matrix','translation','rotation','scale','children')):
        raise ValueError('Unsupported transformed/hierarchical glTF: '+str(path))
    buffers=[(path.parent/b['uri']).read_bytes() for b in data['buffers']]
    def accessor(index):
        a=data['accessors'][index];v=data['bufferViews'][a['bufferView']]
        if 'sparse' in a or 'byteStride' in v:raise ValueError('Unsupported sparse/interleaved accessor')
        dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
        width={'VEC3':3,'VEC2':2,'SCALAR':1}[a['type']]
        return np.frombuffer(buffers[v['buffer']],dtype=dtype,count=a['count']*width,
                             offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width)
    lines=['mtllib '+path.stem+'.mtl'];offset=1;materials=[]
    for primitive in data['meshes'][0]['primitives']:
        if primitive.get('mode',4)!=4:raise ValueError('Only triangles supported')
        attrs=primitive['attributes'];p=accessor(attrs['POSITION']);n=accessor(attrs['NORMAL']);uv=accessor(attrs['TEXCOORD_0'])
        material=data.get('materials',[{}])[primitive.get('material',0)]
        material_name=material.get('name','surface')
        lines.append('usemtl '+material_name)
        if material_name not in [x[0] for x in materials]:materials.append((material_name,material))
        # (x,y,z) glTF -> (x,-z,y) Gazebo, determinant +1.
        for values in p:lines.append('v %.7g %.7g %.7g'%(values[0],-values[2],values[1]))
        for values in uv:lines.append('vt %.7g %.7g'%(values[0],1-values[1]))
        for values in n:lines.append('vn %.7g %.7g %.7g'%(values[0],-values[2],values[1]))
        indices=accessor(primitive['indices']).ravel().reshape(-1,3)+offset
        for face in indices:lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in face))
        offset+=len(p)
    output=path.with_suffix('.obj');output.write_text('\n'.join(lines))
    mtl=[]
    for name,material in materials:
        mtl.extend(['newmtl '+name,'Kd 1 1 1'])
        texture=material.get('pbrMetallicRoughness',{}).get('baseColorTexture',{}).get('index')
        if texture is not None:
            image=data['images'][data['textures'][texture]['source']]['uri']
            mtl.append('map_Kd '+image)
    path.with_suffix('.mtl').write_text('\n'.join(mtl)+'\n')
    print(output.name, 'triangles',sum(s.startswith('f ') for s in lines))


if __name__=='__main__':
    for path in ROOT.glob('*/*.gltf'):convert(path)
    # A UV-tiled visual plane; the ground's infinite physical plane is retained.
    (ROOT/'sand.obj').write_text('v -100 -100 0\nv 100 -100 0\nv 100 100 0\nv -100 100 0\n'
        'vt 0 0\nvt 50 0\nvt 50 50\nvt 0 50\nvn 0 0 1\nf 1/1/1 2/2/1 3/3/1\nf 1/1/1 3/3/1 4/4/1\n')
