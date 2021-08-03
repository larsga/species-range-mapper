
# species-range-mapper

Two simple Python 2.x scripts to generate maps of the geographic
distribution of a species from a dataset listing individual locations
where the species has been observed.

It has two independent parts.

## build_cells.py

This script reads dumps of species observations from
[GBIF.org](https://www.gbif.org/) and outputs a JSON file with
configuration and map grid cells where the species was observed.

By default it smooths out the cell structure somewhat.

Run it with:

```
python build_cells.py path/to/occurrences.txt cells.json
```

There are configuration parameters in the script.

## cells_to_regions.py

This script reads the above JSON file and outputs a merged and
smoothed GeoJSON file with polygons outlining the regions where the
species can be found.

The input JSON file is trivially simple, which means the input species
observations do not need to come from GBIF.

Run it with:

```
python cells_to_regions.py cells.json species-range.json
```

Again there are configuration parameters in the script.

## Using the output

The GeoJSON file can be loaded into most GIS software, like QGIS,
mapnik, and so on, to produce maps.

[Example map made with
mapnik](https://commons.wikimedia.org/wiki/File:Myrica-gale-distribution-map.svg). The
dark outline is directly rendered from a GeoJSON file produced with
this script (and touched up using QGIS).
