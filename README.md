# Lanewise data packs

Offline data for the [Lanewise](https://github.com/salahag-dev/me-navigation) navigation app: one pack per
region, built from OpenStreetMap by the workflow in this repository and published as a release.

Each pack holds:

- `map.pmtiles`: vector map tiles (OpenMapTiles schema), built with [Planetiler](https://github.com/onthegomap/planetiler).
- `routing.tar`: [Valhalla](https://github.com/valhalla/valhalla) routing tiles, including turn lanes, speed
  limits and country borders, for routing and map matching on the phone.
- `manifest.json`: where the data came from and how fresh it is (see below), and each file's size and SHA-256.

## How fresh is a pack?

`manifest.json` records:

- `source.osm_data_timestamp`: the moment the OpenStreetMap data was taken, read from the replication
  timestamp inside the source extract. This is the date the app shows.
- `source.url`, `source.md5`, `source.last_modified`: the exact [Geofabrik](https://download.geofabrik.de)
  extract used. The workflow verifies Geofabrik's MD5 before building.
- `build.built_at`, `build.run`, `build.tools`: when the pack was built, the workflow run that built it
  (its log is public), and the tool versions.

Geofabrik updates its extracts daily, so a pack is as fresh as the day its workflow ran.

## Building a region

Regions are defined in `regions/` (source extract and clip). Run **Actions → Build region pack** with the
region id. The release tag is the region and the OpenStreetMap data time, for example `uae-20261025-2100`.

## Licence

The data packs are derived from OpenStreetMap and available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/): © OpenStreetMap contributors.
The workflow and scripts in this repository are MIT licensed.
