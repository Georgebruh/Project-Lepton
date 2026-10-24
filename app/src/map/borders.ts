import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { Map as MapLibreMap } from 'maplibre-gl'

/* Which lines the map draws at each zoom, so the whole country opens clean and quick to draw. */

/** The zoom the coastlines and the street map's lines start at. */
export const ISLANDS_ZOOM = 6

/** The zoom the towns' borders start at, and the coastlines start to go. */
export const CITIES_ZOOM = 8

/** How many zoom levels a fade takes: from nothing to fully drawn. */
export const FADE_ZOOMS = 0.75

/** An opacity that rises with the zoom, from 0 at `from` to `opacity` FADE_ZOOMS later. */
export function fadeIn(from: number, opacity = 1): ExpressionSpecification {
  return ['interpolate', ['linear'], ['zoom'], from, 0, from + FADE_ZOOMS, opacity]
}

/** ph_islands.json: one polygon per island, its outer coast only. */
export type Islands = FeatureCollection<Polygon | MultiPolygon>

const SOURCE = 'islands'
export const ISLANDS_LAYER = 'islands-line'

/** The coastlines' width in px. */
const ISLAND_LINE = 0.75

/** Adds the coastlines, in `color` (the towns' borders' color), on top of the layers so far. */
export function addIslands(map: MapLibreMap, islands: Islands, color: string) {
  map.addSource(SOURCE, { type: 'geojson', data: islands })
  map.addLayer({
    id: ISLANDS_LAYER,
    type: 'line',
    source: SOURCE,
    minzoom: ISLANDS_ZOOM,
    maxzoom: CITIES_ZOOM + FADE_ZOOMS,
    layout: { 'line-join': 'round' },
    paint: {
      'line-color': color,
      'line-width': ISLAND_LINE,
      'line-opacity': [
        'interpolate',
        ['linear'],
        ['zoom'],
        ISLANDS_ZOOM,
        0,
        ISLANDS_ZOOM + FADE_ZOOMS,
        1,
        CITIES_ZOOM,
        1,
        CITIES_ZOOM + FADE_ZOOMS,
        0,
      ],
    },
  })
}
