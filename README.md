# Lanewise data packs

Offline data for the [Lanewise](https://github.com/salahag-dev/me-navigation) navigation app: one pack per
region, built from OpenStreetMap by the workflow in this repository and published as a release.

Each pack holds:

- `map.pmtiles`: vector map tiles (OpenMapTiles schema), built with [Planetiler](https://github.com/onthegomap/planetiler).
- `routing.tar.xz`: [Valhalla](https://github.com/valhalla/valhalla) routing tiles, including turn lanes, speed
  limits and country borders, for routing and map matching on the phone. It is compressed for download (about
  a quarter of its size); the app unpacks it once, since Valhalla reads the plain tar.
- `coverage.geojson`: the area the pack covers.
- `manifest.json`: where the data came from and how fresh it is (see below), and each file's size and SHA-256
  (for `routing.tar.xz`, also the unpacked tar's).

## The catalog

[`catalog.json`](catalog.json) lists every pack the app can download, newest first for each region, with its
data time, download and installed sizes, and each file's URL and SHA-256. The app reads it from
`https://raw.githubusercontent.com/salahag-dev/lanewise-data/main/catalog.json` when you check for updates.
The workflow rewrites and commits it after each build, so its history is the history of published packs.

## How fresh is a pack?

`manifest.json` records:

- `source.osm_data_timestamp`: the moment the OpenStreetMap data was taken, read from the replication
  timestamp inside the source extract. This is the date the app shows.
- `source.download_url`, `source.md5`, `source.last_modified`: the exact [Geofabrik](https://download.geofabrik.de)
  extract used. The workflow verifies Geofabrik's MD5 before building.
- `build.built_at`, `build.run`, `build.tools`: when the pack was built, the workflow run that built it
  (its log is public), and the tool versions.

Geofabrik updates its extracts daily. The workflow runs every Monday at 04:00 UTC and rebuilds each region
whose extract has changed since its last pack, so packs are at most about a week old.

## Regions

Regions are defined in [`regions/`](regions): the country (its ISO code), the Geofabrik extract it comes from,
and a margin. A region covers the country's OpenStreetMap border plus the margin (20 km), so roads that cross
a border briefly stay routable. Today: the six GCC countries, from Geofabrik's GCC States extract.

To build now, run **Actions → Build region packs** with a region id, or `all`. A region is skipped when
Geofabrik has nothing newer than its published pack, unless you tick *force*. The release tag is the region
and the OpenStreetMap data time, for example `uae-20261025-2121`. Two packs are kept per region (the newest,
and the one before so a download in progress can finish); older ones are deleted.

## Licence

The data packs are derived from OpenStreetMap and available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/): © OpenStreetMap contributors.
The workflow and scripts in this repository are MIT licensed.
