"""Writes a region's coverage: its OpenStreetMap country border, widened by a margin.

The region's data is clipped to this polygon. The margin keeps roads that cross a border
briefly (the Hatta road through Oman, say) and the first stretch past each border crossing.
The polygon also travels in the pack, so the app can show what a pack covers.

Prints bbox=MINLON,MINLAT,MAXLON,MAXLAT for the workflow.

usage: coverage.py REGION_JSON BORDER_GEOJSON OUT_GEOJSON
"""
import json
import math
import sys

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

region_file, border_file, out_file = sys.argv[1:4]
region = json.load(open(region_file, encoding='utf-8'))
code = region['country']

# osmium export of the relations tagged with the country code: keep the country's own border.
borders = [f for f in json.load(open(border_file, encoding='utf-8'))['features']
           if f['properties'].get('boundary') == 'administrative' and f['properties'].get('admin_level') == '2'
           and f['properties'].get('ISO3166-1:alpha2') == code]
if len(borders) != 1:
    sys.exit(f"Expected one country border tagged ISO3166-1:alpha2={code}, found {len(borders)}")
border = shape(borders[0]['geometry'])

# Widen in metres, in a projection centred on the country, then back to degrees.
centre = border.centroid
local = f'+proj=aeqd +lat_0={centre.y} +lon_0={centre.x} +units=m'
to_metres = Transformer.from_crs('EPSG:4326', local, always_xy=True).transform
to_degrees = Transformer.from_crs(local, 'EPSG:4326', always_xy=True).transform
margin = region['margin_km'] * 1000
area = transform(to_metres, border).simplify(100).buffer(margin).simplify(500)
area = transform(to_degrees, area)

geometry = mapping(area)
geometry['coordinates'] = json.loads(json.dumps(geometry['coordinates']), parse_float=lambda x: round(float(x), 5))
relation = borders[0].get('id', '')
coverage = {
    'type': 'FeatureCollection',
    'features': [{
        'type': 'Feature',
        'properties': {
            'region': region['id'],
            'name': region['name'],
            'border': f"OpenStreetMap relation {relation.lstrip('r')} (ISO3166-1:alpha2={code})" if relation else f"ISO3166-1:alpha2={code}",
            'margin_km': region['margin_km'],
        },
        'geometry': geometry,
    }],
}
json.dump(coverage, open(out_file, 'w', encoding='utf-8'), separators=(',', ':'))

west, south, east, north = area.bounds
bbox = [math.floor(west * 1000) / 1000, math.floor(south * 1000) / 1000, math.ceil(east * 1000) / 1000, math.ceil(north * 1000) / 1000]
print(f"bbox={','.join(str(v) for v in bbox)}")
print(f"{region['name']}: {coverage['features'][0]['properties']['border']} plus {region['margin_km']} km, "
      f"{sum(len(p.exterior.coords) for p in getattr(area, 'geoms', [area]))} points, bbox {bbox}", file=sys.stderr)
