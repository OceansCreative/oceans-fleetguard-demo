# Bundled vector basemap (`basemap.geojson`)

A small, simplified land/coastline outline of the demo area
(Matsue / Yasugi / Yonago, including Lake Shinji and the Nakaumi lagoon).

It is rendered **below** the OpenStreetMap tile layer, so:

- on a normal network, OSM tiles provide the full street map;
- offline or in a locked-down network (no tile CDN access), the map still
  shows recognizable coastline and water instead of a blank rectangle.

## Source & licence

Derived from the National Land Numerical Information (administrative area
boundaries), Ministry of Land, Infrastructure, Transport and Tourism (Japan) —
国土数値情報（行政区域データ）国土交通省 — via the
[`niiyz/JapanCityGeoJson`](https://github.com/niiyz/JapanCityGeoJson) dataset.

Thirteen municipalities around the demo area (Matsue, Izumo, Oda, Yasugi,
Unnan, Okuizumo, Yonago, Sakaiminato, Kotoura, Hiezu, Daisen, Nanbu, Hoki) were
cropped to the demo bounding box and simplified (Douglas–Peucker, ~28 m
tolerance). Attribution is shown in the map's attribution control.

## `rail.geojson` — railway lines & stations

Railway routes and station points for the same area, rendered beneath the tile
layer so the offline map shows the rail network too. Built from the
[`piuccio/open-data-jp-railway-lines`](https://github.com/piuccio/open-data-jp-railway-lines)
dataset, which is derived from **[ekidata.jp](https://ekidata.jp/)** station/line
data (lines are drawn by connecting each line's stations in order, then clipped
to the demo bounding box). Credited in the map attribution.

## `labels.geojson` — place & water names

Point labels for the map: one per municipality (label point = the vertex
centroid of each city's largest polygon, from the same boundary data above) plus
a few hand-placed water-body names (Sea of Japan, Lake Shinji, Nakaumi). Drawn
as text divIcons in the basemap pane, so OSM's own labels take over when tiles
are available.
