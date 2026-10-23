import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { Map as MapLibreMap } from 'maplibre-gl'

/*
 * F14: which lines the map draws at each zoom, so the whole country opens clean and quick to draw:
 *   - the country's view, below ISLANDS_ZOOM: no lines at all, only the land, the water and
 *     Quezon City's color; not even the street map's roads and rivers (basemap.ts);
 *   - from ISLANDS_ZOOM: each island's coastline (ph_islands.json, F2's island_outlines), with the
 *     street map's roads and rivers;
 *   - from CITIES_ZOOM: the borders of the cities and municipalities (CityMap), while the
 *     coastlines fade out, since the borders follow the coast too, more closely.
 * Each fades in over FADE_ZOOMS. A layer is not drawn at all below the zoom it starts at (its
 * minzoom), so the country's view never draws the 1,642 borders. The fades are paint values that
 * change with the zoom alone, which MapLibre works out once a frame for the whole layer: they add
 * no shader (app/README.md, "Keeping the map smooth").
 */

/** The zoom the coastlines and the street map's lines start at: a step in from the whole country (about 5 on a laptop). */
export const ISLANDS_ZOOM = 6

/** The zoom the towns' borders start at, and the coastlines start to go: a few provinces fill the screen. */
export const CITIES_ZOOM = 8

/** How many zoom levels a fade takes: from nothing to fully drawn. */
export const FADE_ZOOMS = 0.75

/** An opacity that rises with the zoom, from 0 at `from` to `opacity` FADE_ZOOMS later. */
export function fadeIn(from: number, opacity = 1): ExpressionSpecification {
  return ['interpolate', ['linear'], ['zoom'], from, 0, from + FADE_ZOOMS, opacity]
}

/** ph_islands.json: one polygon per island, its outer coast only (F2). */
export type Islands = FeatureCollection<Polygon | MultiPolygon>

const SOURCE = 'islands'
export const ISLANDS_LAYER = 'islands-line'

/** The coastlines' width in px: thinner than a town's border (1 px), since they show the whole of a large island. */
const ISLAND_LINE = 0.75

/**
 * Adds the coastlines, in `color` (the towns' borders' color), on top of the layers so far: CityMap
 * adds them just before the towns' borders. They fade in from ISLANDS_ZOOM and out from CITIES_ZOOM.
 */
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
