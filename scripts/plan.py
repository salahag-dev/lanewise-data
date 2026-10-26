"""Decides which regions a run builds.

A region is built when it is asked for (every region, on the weekly schedule)
and Geofabrik's extract has changed since the region's newest published pack,
by comparing Geofabrik's MD5 with the one in catalog.json. FORCE builds anyway.

usage: plan.py   (env REGION: a region id, or all; FORCE: true to build regardless)
"""
import glob
import json
import os
import sys
import urllib.request

asked = os.environ.get('REGION') or 'all'
force = os.environ.get('FORCE') == 'true'
regions = {}
for path in sorted(glob.glob('regions/*.json')):
    region = json.load(open(path, encoding='utf-8'))
    if region['id'] != os.path.basename(path)[:-len('.json')]:
        sys.exit(f"{path}: id {region['id']!r} must match the file name")
    regions[region['id']] = region
if asked != 'all' and asked not in regions:
    sys.exit(f"No region {asked!r}. Regions: {', '.join(regions)}")

try:
    catalog = json.load(open('catalog.json', encoding='utf-8'))
except FileNotFoundError:
    catalog = {'regions': []}
published = {r['id']: r['packs'][0]['source'] for r in catalog['regions'] if r['packs']}

md5s = {}


def current_md5(url):
    if url not in md5s:
        with urllib.request.urlopen(url + '.md5', timeout=60) as response:
            md5s[url] = response.read().decode().split()[0]
    return md5s[url]


build, rows = [], []
for id, region in regions.items():
    if asked not in ('all', id):
        continue
    if force:
        reason = 'asked to rebuild'
    elif id not in published:
        reason = 'no pack yet'
    elif current_md5(region['source']) != published[id]['md5']:
        reason = f"newer data than the pack from {published[id]['osm_data_timestamp']}"
    else:
        rows.append(f"| {region['name']} | skipped: no newer data than {published[id]['osm_data_timestamp']} |")
        continue
    build.append(id)
    rows.append(f"| {region['name']} | build: {reason} |")

print('\n'.join(rows))
with open(os.environ.get('GITHUB_OUTPUT', os.devnull), 'a') as out:
    out.write(f'regions={json.dumps(build)}\n')
with open(os.environ.get('GITHUB_STEP_SUMMARY', os.devnull), 'a', encoding='utf-8') as summary:
    summary.write('| Region | This run |\n|---|---|\n' + '\n'.join(rows) + '\n')
