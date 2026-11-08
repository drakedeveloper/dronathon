"""Fetch selected real CC0 coastal scans, preserving provenance and checksums."""
import json
from pathlib import Path
from scripts.fetch_scene_assets import request,fetch,ROOT


def main():
    records=[]
    for asset in ('coastal_cliff_02','coast_line_02','coast_rocks_03','island_tree_02'):
        files=json.loads(request('https://api.polyhaven.com/files/'+asset))
        model=files['gltf']['1k']['gltf']
        records.append(fetch(asset,asset+'.gltf',model))
        for name,metadata in model['include'].items():records.append(fetch(asset,name,metadata))
        print('Downloaded',asset,flush=True)
    for asset in ('aerial_rocks_02','coast_sand_rocks_02','aerial_grass_rock'):
        files=json.loads(request('https://api.polyhaven.com/files/'+asset))
        for channel,name in [('Diffuse','diffuse.jpg'),('nor_gl','normal.jpg'),('Rough','roughness.jpg')]:
            records.append(fetch(asset,name,files[channel]['2k']['jpg']))
        print('Downloaded',asset,flush=True)
    manifest={'provider':'Poly Haven','license':'CC0-1.0','license_url':'https://polyhaven.com/license','files':records}
    (ROOT/'cinematic-manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Verified',round(sum(r['bytes'] for r in records)/1048576,1),'MiB',flush=True)


if __name__=='__main__':main()
