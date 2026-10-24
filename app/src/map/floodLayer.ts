import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import { useEffect, useState } from 'react'
import maplibregl from '../lib/maplibre.ts'
import { SLOTS } from './layerOrder.ts'
import { CROSSFADE_MS } from './motion.ts'
import { isSourceError, whenSourceReady } from './sourceReady.ts'
import { tokenColor } from './tokens.ts'

/* NOAH's flood zones on the map, from the Layers panel. */

/** NOAH's maps, by how rare their rain is: once in 5, 25 or 100 years on average. */
export const FLOOD_PERIODS = [5, 25, 100] as const
export type FloodPeriod = (typeof FLOOD_PERIODS)[number]

/** The map the flood switch shows until the reader picks another: the 25-year map. */
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

/** The tiles' layer in each PMTiles file (src/noah_national.py's tippecanoe -l). */
const TILE_LAYER = 'flood'

/** Lets MapLibre read pmtiles:// addresses, once per page. */
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

/** Adds NOAH's map for `period`, hidden. */
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

/** Shows NOAH's map for `period` (null: none) and hides the others. */
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

/** Shows NOAH's map for `period` on `map` (null: none) and says how it is doing. */
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
