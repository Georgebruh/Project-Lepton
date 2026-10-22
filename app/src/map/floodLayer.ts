import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useState } from 'react'
import { SLOTS } from './layerOrder.ts'
import { CROSSFADE_MS } from './motion.ts'
import { isSourceError, whenSourceReady } from './sourceReady.ts'
import { tokenColor } from './tokens.ts'

/*
 * F13: NOAH's flood zones on the map, from the Layers panel: the flood hazard map for a 5-,
 * 25- or 100-year rain (UP NOAH Center, ODbL), as F2 simplified it for the browser
 * (public/data/noah_<T>yr.json, written by src/app_data.py). Each map is one GeoJSON source
 * and one fill layer, added the first time it is chosen, in the flood slot (layerOrder.ts):
 * over LEPTON's fills and under the street map's names. Each hazard level takes its blue
 * (map/hazard-low, -medium, -high in Figma), and the city and barangay colors show a little
 * through.
 *
 * A file is 7.6 to 9.0 MB (1.3 to 1.5 MB sent compressed). MapLibre fetches it and cuts it into
 * tiles in its worker, so the page does not stall, and keeps it while the map lives, so a map
 * shown before comes back at once. useFloodZones tells the panel and the legend how the chosen
 * map is doing: loading, shown, or failed (the rest of the map works as usual).
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
 * whichever map is shown by then, so choosing it again fetches it again.
 */
function addFlood(map: MapLibreMap, period: FloodPeriod) {
  const id = floodId(period)
  map.addSource(id, { type: 'geojson', data: `/data/noah_${period}yr.json`, attribution: CREDIT })
  map.addLayer(
    {
      id,
      type: 'fill',
      source: id,
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
    if (isSourceError(event, id)) {
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
