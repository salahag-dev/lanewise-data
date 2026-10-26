"""Writes manifest.json and notes.md for a built region pack.

The manifest is what the Lanewise app reads to show how fresh a pack is and
to check downloads: where the OpenStreetMap data came from and when it was
taken, when and how the pack was built, and each file's size and checksum.

usage: manifest.py REGION_JSON SOURCE_PBF SOURCE_MD5 SOURCE_LAST_MODIFIED OUT_DIR
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys

region_file, source_pbf, source_md5, last_modified, out_dir = sys.argv[1:6]
region = json.load(open(region_file, encoding='utf-8'))


def osm_info(path):
    """The data time from the extract itself: the replication timestamp in its header, and the newest object."""
    info = json.loads(subprocess.check_output(['osmium', 'fileinfo', '--extended', '--json', path]))
    header = info.get('header', {}).get('option', {})
    data = info.get('data', {}).get('timestamp', {})
    return {
        'replication_timestamp': header.get('osmosis_replication_timestamp') or header.get('timestamp'),
        'replication_sequence': header.get('osmosis_replication_sequence_number'),
        'newest_object': data.get('last'),
    }


def describe(name):
    path = os.path.join(out_dir, name)
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            digest.update(block)
    return {'name': name, 'bytes': os.path.getsize(path), 'sha256': digest.hexdigest()}


osm = osm_info(source_pbf)
built = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
files = [describe(n) for n in sorted(os.listdir(out_dir)) if n.endswith(('.tar', '.pmtiles', '.sqlite'))]
manifest = {
    'schema': 1,
    'region': {'id': region['id'], 'name': region['name'], 'bbox': region['bbox'], 'clip_note': region.get('clip_note', '')},
    'source': {
        'name': region['source_name'],
        'url': region['source'],
        'md5': source_md5,
        'last_modified': last_modified,
        'osm_data_timestamp': osm['replication_timestamp'],
        'osm_replication_sequence': osm['replication_sequence'],
        'newest_object': osm['newest_object'],
        'licence': 'Open Database License (ODbL) 1.0, (c) OpenStreetMap contributors',
    },
    'build': {
        'built_at': built,
        'run': os.environ.get('RUN_URL', ''),
        'tools': {
            'valhalla': os.environ.get('VALHALLA_VERSION', ''),
            'planetiler': os.environ.get('PLANETILER_VERSION', ''),
            'osmium': subprocess.check_output(['osmium', '--version'], text=True).splitlines()[0],
        },
    },
    'files': files,
}
json.dump(manifest, open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8'), indent=2)

lines = [
    f"# {region['name']}",
    '',
    f"OpenStreetMap data as of **{osm['replication_timestamp']}** (from {region['source_name']}, newest edit {osm['newest_object']}).",
    f"Built {built} with Valhalla {manifest['build']['tools']['valhalla']} and Planetiler {manifest['build']['tools']['planetiler']}.",
    '',
    '| File | Size | SHA-256 |',
    '|---|---|---|',
]
lines += [f"| {f['name']} | {f['bytes'] / 1e6:.1f} MB | `{f['sha256']}` |" for f in files]
lines += ['', f"Source: {region['source']} (md5 `{source_md5}`, last modified {last_modified}).", '',
          'Map data (c) OpenStreetMap contributors, available under the Open Database License.']
open(os.path.join(out_dir, 'notes.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(json.dumps(manifest, indent=2))
