"""Writes manifest.json and notes.md for a built region pack.

The manifest is what the Lanewise app reads to show how fresh a pack is and
to check downloads: where the OpenStreetMap data came from and when it was
taken, what area it covers, when and how the pack was built, and each file's
size and checksum. routing.tar travels compressed as routing.tar.xz; its
entry also describes the unpacked tar, which is what Valhalla reads.

usage: manifest.py REGION_JSON SOURCE_PBF SOURCE_MD5 SOURCE_LAST_MODIFIED SOURCE_DOWNLOAD_URL ROUTING_TAR OUT_DIR
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys

region_file, source_pbf, source_md5, last_modified, download_url, routing_tar, out_dir = sys.argv[1:8]
region = json.load(open(region_file, encoding='utf-8'))
coverage = json.load(open(os.path.join(out_dir, 'coverage.geojson'), encoding='utf-8'))['features'][0]


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


def describe(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            digest.update(block)
    return {'name': os.path.basename(path), 'bytes': os.path.getsize(path), 'sha256': digest.hexdigest()}


def bounds(geometry):
    points = [p for polygon in (geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']])
              for ring in polygon for p in ring]
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


osm = osm_info(source_pbf)
built = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
routing = describe(os.path.join(out_dir, 'routing.tar.xz'))
routing.update({'compression': 'xz', 'unpacked': describe(routing_tar)})
files = [describe(os.path.join(out_dir, 'map.pmtiles')), routing, describe(os.path.join(out_dir, 'coverage.geojson'))]
manifest = {
    'schema': 2,
    'region': {
        'id': region['id'],
        'name': region['name'],
        'country': region['country'],
        'bbox': bounds(coverage['geometry']),
        'coverage': {
            'file': 'coverage.geojson',
            'border': coverage['properties']['border'],
            'margin_km': region['margin_km'],
            'note': f"The country's OpenStreetMap border plus {region['margin_km']} km, so roads that cross a border briefly stay routable.",
        },
    },
    'source': {
        'name': region['source_name'],
        'url': region['source'],
        'download_url': download_url,
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

download = sum(f['bytes'] for f in files)
installed = sum(f.get('unpacked', f)['bytes'] for f in files)
lines = [
    f"# {region['name']}",
    '',
    f"OpenStreetMap data as of **{osm['replication_timestamp']}** (from {region['source_name']}, newest edit {osm['newest_object']}).",
    f"Covers {manifest['region']['coverage']['border']} plus {region['margin_km']} km.",
    f"Built {built} with Valhalla {manifest['build']['tools']['valhalla']} and Planetiler {manifest['build']['tools']['planetiler']}.",
    f"Download {download / 1e6:.1f} MB, {installed / 1e6:.1f} MB once installed.",
    '',
    '| File | Size | SHA-256 |',
    '|---|---|---|',
]
for f in files:
    lines.append(f"| {f['name']} | {f['bytes'] / 1e6:.1f} MB | `{f['sha256']}` |")
    if 'unpacked' in f:
        lines.append(f"| ↳ {f['unpacked']['name']} (unpacked) | {f['unpacked']['bytes'] / 1e6:.1f} MB | `{f['unpacked']['sha256']}` |")
lines += ['', f"Source: {download_url} (md5 `{source_md5}`, last modified {last_modified}).", '',
          'Map data (c) OpenStreetMap contributors, available under the Open Database License.']
open(os.path.join(out_dir, 'notes.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(json.dumps(manifest, indent=2))
