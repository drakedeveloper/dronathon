"""Fetch a small, checksummed CC0 scene pack through Poly Haven's public API."""
from pathlib import Path
import hashlib
import json
import http.client
import time
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'sim' / 'assets'
HEADERS = {'User-Agent': 'SKYFORGE-Hackathon/1.0 (local simulation asset setup)'}


def request(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=90) as response:
                return response.read()
        except (OSError,http.client.IncompleteRead):
            if attempt==2:raise
            time.sleep(attempt+1)


def fetch(asset, relative, metadata):
    target = (ROOT / asset / relative).resolve()
    if not target.is_relative_to((ROOT / asset).resolve()):
        raise ValueError('Asset path escapes destination')
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or hashlib.md5(target.read_bytes()).hexdigest() != metadata['md5']:
        if metadata.get('size',0)>8*1024**2:
            partial=target.with_suffix(target.suffix+'.partial')
            command=['curl.exe' if __import__('os').name=='nt' else 'curl','--fail','--location','--silent','--show-error',
                     '--retry','3','--retry-all-errors','--continue-at','-','--output',str(partial),metadata['url']]
            subprocess.run(command,check=True)
            body=partial.read_bytes()
        else:body = request(metadata['url'])
        if hashlib.md5(body).hexdigest() != metadata['md5']:
            raise ValueError('Asset checksum mismatch: ' + relative)
        target.write_bytes(body)
    body = target.read_bytes()
    return {'path': str(target.relative_to(ROOT)), 'source': metadata['url'],
            'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for asset in ('rock_face_01', 'concrete_road_barrier_02'):
        files = json.loads(request('https://api.polyhaven.com/files/' + asset))
        gltf = files['gltf']['1k']['gltf']
        records.append(fetch(asset, asset + '.gltf', gltf))
        for name, metadata in gltf['include'].items():
            records.append(fetch(asset, name, metadata))
    asset = 'coast_sand_02'
    files = json.loads(request('https://api.polyhaven.com/files/' + asset))
    for channel, filename in (('Diffuse', 'diffuse.jpg'), ('nor_gl', 'normal.jpg'), ('Rough', 'roughness.jpg')):
        records.append(fetch(asset, filename, files[channel]['1k']['jpg']))
    manifest = {'license': 'CC0-1.0', 'license_url': 'https://polyhaven.com/license',
                'provider': 'Poly Haven', 'files': records}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Verified {len(records)} files, {sum(r["bytes"] for r in records)/1048576:.1f} MiB')


if __name__ == '__main__':
    main()
