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

Five municipalities (Matsue 32201, Izumo 32203, Yasugi 32206, Yonago 31202,
Sakaiminato 31204) were cropped to the demo bounding box and simplified
(Douglas–Peucker, ~110 m tolerance) down to ~14 KB. Attribution is shown in the
map's attribution control.
