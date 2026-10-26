"""Writes catalog.json, the list of downloadable packs the app reads, and prunes old packs.

Every release that carries a manifest.json is a pack. Packs are grouped by
region, newest data first, and the newest KEEP per region stay: the newest is
the one the app offers, and the one before stays so a download started from
an older catalog can still finish. Older packs are deleted with their tags.

usage: catalog.py KEEP [--dry-run]
"""
import json
import os
import subprocess
import sys
import urllib.request

keep = int(sys.argv[1])
dry_run = '--dry-run' in sys.argv
repo = os.environ.get('GITHUB_REPOSITORY', 'salahag-dev/lanewise-data')


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def pack(release, assets, manifest):
    files = []
    for f in manifest['files']:
        asset = assets.get(f['name'])
        if asset is None or asset['size'] != f['bytes']:
            raise ValueError(f"{f['name']} is missing or not the size its manifest says")
        files.append({**f, 'url': asset['browser_download_url']})
    source = manifest['source']
    return {
        'tag': release['tag_name'],
        'published_at': release['published_at'],
        'source': {k: source[k] for k in ('name', 'osm_data_timestamp', 'newest_object', 'last_modified', 'md5')},
        'built_at': manifest['build']['built_at'],
        'run': manifest['build']['run'],
        'manifest_url': assets['manifest.json']['browser_download_url'],
        'download_bytes': sum(f['bytes'] for f in files),
        'installed_bytes': sum(f.get('unpacked', f)['bytes'] for f in files),
        'files': files,
    }


lines = subprocess.check_output(['gh', 'api', '--paginate', f'repos/{repo}/releases', '--jq', '.[] | @json'], text=True).splitlines()
by_region = {}
for release in (json.loads(line) for line in lines if line.strip()):
    assets = {a['name']: a for a in release['assets']}
    if release['draft'] or 'manifest.json' not in assets:
        continue
    manifest = fetch_json(assets['manifest.json']['browser_download_url'])
    by_region.setdefault(manifest['region']['id'], []).append((release, assets, manifest))

regions = []
for id, packs in by_region.items():
    packs.sort(key=lambda p: (p[2]['source']['osm_data_timestamp'], p[2]['build']['built_at']), reverse=True)
    # Only packs the app can use count towards KEEP, so a broken new pack never pushes out the last good one.
    listed, newest = [], None
    for release, assets, manifest in packs:
        if len(listed) == keep:
            print(f"{id}: pruning {release['tag_name']}")
            if not dry_run:
                subprocess.run(['gh', 'release', 'delete', release['tag_name'], '-R', repo, '--cleanup-tag', '--yes'], check=True)
        elif manifest['schema'] < 2:
            print(f"{id}: leaving {release['tag_name']} out, its manifest predates compressed routing data")
        else:
            try:
                listed.append(pack(release, assets, manifest))
                newest = newest or manifest['region']
            except ValueError as problem:
                print(f"{id}: leaving {release['tag_name']} out: {problem}")
    if listed:
        regions.append({'id': id, 'name': newest['name'], 'country': newest['country'], 'bbox': newest['bbox'],
                        'coverage_note': newest['coverage']['note'], 'packs': listed})
        print(f"{id}: offering {', '.join(p['tag'] for p in listed)}")

catalog = {
    'schema': 1,
    'about': 'Offline data packs for the Lanewise app, built from OpenStreetMap. '
             'Map data (c) OpenStreetMap contributors, available under the Open Database License.',
    'repository': f'https://github.com/{repo}',
    'regions': sorted(regions, key=lambda r: r['name']),
}
with open('catalog.json', 'w', encoding='utf-8', newline='\n') as out:
    json.dump(catalog, out, indent=2, ensure_ascii=False)
    out.write('\n')
