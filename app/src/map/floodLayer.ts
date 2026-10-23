import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import { useEffect, useState } from 'react'
import maplibregl from '../lib/maplibre.ts'
import { SLOTS } from './layerOrder.ts'
import { CROSSFADE_MS } from './motion.ts'
import { isSourceError, whenSourceReady } from './sourceReady.ts'
import { tokenColor } from './tokens.ts'

/*
 * F13: NOAH's flood zones on the map, from the Layers panel: the flood hazard map for a 5-,
 * 25- or 100-year rain (UP NOAH Center, ODbL). Each map is one source and one fill layer, added
 * the first time it is chosen, in the flood slot (layerOrder.ts): over LEPTON's fills and under
 * the street map's names. Each hazard level takes its blue (map/hazard-low, -medium, -high in
 * Figma), and the city and barangay colors show a little through.
 *
 * F14: the whole Philippines, every province NOAH has mapped, not only Metro Manila. Each map is
 * one PMTiles file of vector tiles (public/data/noah_flood_<T>yr.pmtiles, written by
 * src/noah_national.py with tippecanoe): the browser asks the file for the tiles in view only,
 * with HTTP range requests, through the pmtiles protocol added to MapLibre (Vercel and Vite both
 * answer range requests). The tiles stop at zoom 11 (about 10 m a unit); MapLibre stretches them
 * further in. useFloodZones tells the panel and the legend how the chosen map is doing: loading,
 * shown, or failed (the rest of the map works as usual).
 */

/** NOAH's maps, by how rare their rain is: once in 5, 25 or 100 years on average. */
export const FLOOD_PERIODS = [5, 25, 100] as const
export type FloodPeriod = (typeof FLOOD_PERIODS)[number]

/** The map the flood switch shows until the reader picks another: the 25-year map, as in Figma. */
export const DEFAULT_FLOOD: FloodPeriod = 25

/** NOAH's hazard levels (the files' `var`), their depths (NOAH's metadata_flood.txt) and their tokens. */
export const FLOOD_LEVELS = [
  { level: 1, name: 'Low', depth: 'up to 0.5 m', token: 'map-hazard-low' },
  { level: 2, name: 'Medium', depth: '0.5–1.5 m', token: 'map-hazard-medium' },
  { level: 3, name: 'High', depth: 'over 1.5 m', token: 'map-hazard-high' },
] as const

/** How the chosen map is doing: none chosen, its file on the way, drawn, or its file did not load. */
export type FloodStatus = 'off' | 'loading' | 'shown' | 'failed'

/** How opaque the flood zones are: the city and barangay colors under them show a little. */
const FLOOD_OPACITY = 0.8

const CREDIT = 'Flood hazard: <a href="https://noah.up.edu.ph" target="_blank" rel="noopener">UP NOAH Center</a> (ODbL)'

/** F14: the tiles' layer in each PMTiles file (src/noah_national.py's tippecanoe -l). */
const TILE_LAYER = 'flood'

/** F14: lets MapLibre read pmtiles:// addresses, once per page. */
let protocolAdded = false
function addPmtilesProtocol() {
  if (!protocolAdded) {
    maplibregl.addProtocol('pmtiles', new Protocol().tile)
    protocolAdded = true
  }
}

/** A map's source and layer, which share the id. */
function floodId(period: FloodPeriod) {
  return `noah-${period}yr`
}

/** A zone's fill: its hazard level's blue, from tokens.css. */
function fillColor(element: HTMLElement): ExpressionSpecification {
  const [low, medium, high] = FLOOD_LEVELS.map(({ token }) => tokenColor(element, token))
  return ['match', ['get', 'var'], 1, low, 2, medium, high]
}

/**
 * Adds NOAH's map for `period`, hidden. If its file does not load, the map is removed again,
 * whichever map is shown by then, so choosing it again fetches it again. F14: a single tile
 * that fails (a dropped range request while panning) is not the file failing: MapLibre draws
 * that tile as nothing and asks again later, and the rest of the country stays.
 */
function addFlood(map: MapLibreMap, period: FloodPeriod) {
  const id = floodId(period)
  addPmtilesProtocol()
  map.addSource(id, {
    type: 'vector',
    url: `pmtiles://${window.location.origin}/data/noah_flood_${period}yr.pmtiles`,
    attribution: CREDIT,
  })
  map.addLayer(
    {
      id,
      type: 'fill',
      source: id,
      'source-layer': TILE_LAYER,
      layout: { visibility: 'none' },
      paint: {
        'fill-color': fillColor(map.getContainer()),
        'fill-opacity': 0,
        'fill-opacity-transition': { duration: CROSSFADE_MS, delay: 0 },
      },
    },
    SLOTS.flood,
  )
  const onError = (event: MapEventType['error']) => {
    if (isSourceError(event, id) && !('tile' in event)) {
      map.off('error', onError)
      map.removeLayer(id)
      map.removeSource(id)
    }
  }
  map.on('error', onError)
}

/**
 * Shows NOAH's map for `period` (null: none) and hides the others: hidden, MapLibre does not cut
 * their tiles. A map shown before fades back in; a new one draws as its tiles come. Tells
 * `onStatus` how the map is doing until the returned function is called.
 */
function showFlood(map: MapLibreMap, period: FloodPeriod | null, onStatus: (status: FloodStatus) => void): () => void {
  const shown = period === null ? null : floodId(period)
  if (period !== null && !map.getLayer(floodId(period))) {
    addFlood(map, period)
  }
  for (const other of FLOOD_PERIODS) {
    const id = floodId(other)
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, 'visibility', id === shown ? 'visible' : 'none')
      map.setPaintProperty(id, 'fill-opacity', id === shown ? FLOOD_OPACITY : 0)
    }
  }
  if (!shown) {
    return () => {}
  }
  // Shown once the tiles where the map is now are cut (sourceReady.ts)
  onStatus('loading')
  return whenSourceReady(
    map,
    shown,
    () => onStatus('shown'),
    () => onStatus('failed'),
  )
}

/**
 * Shows NOAH's map for `period` on `map` (null: none) and says how it is doing: 'off' with none
 * chosen, 'loading' until its file has come and its tiles are cut, then 'shown', or 'failed'.
 * retry() fetches a failed map again.
 */
export function useFloodZones(
  map: MapLibreMap | null,
  period: FloodPeriod | null,
): { status: FloodStatus; retry: () => void } {
  const [news, setNews] = useState<{ period: FloodPeriod; status: FloodStatus } | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!map) {
      return
    }
    return showFlood(map, period, (status) => setNews(period === null ? null : { period, status }))
  }, [map, period, attempt])
  const status = period === null ? 'off' : news?.period === period ? news.status : 'loading'
  return { status, retry: () => setAttempt((count) => count + 1) }
}
