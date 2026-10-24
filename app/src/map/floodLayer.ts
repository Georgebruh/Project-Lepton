import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import { useEffect, useState } from 'react'
import maplibregl from '../lib/maplibre.ts'
import { SLOTS } from './layerOrder.ts'
import { shortName, type Cities } from './mapData.ts'
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

/**
 * A zone's fill: its hazard level's blue, from tokens.css. The national tiles hold `var` as text ("1"),
 * the city files as a number, so it is read as a number: compared as text, every zone fell to the high blue.
 */
function fillColor(element: HTMLElement): ExpressionSpecification {
  const [low, medium, high] = FLOOD_LEVELS.map(({ token }) => tokenColor(element, token))
  return ['match', ['to-number', ['get', 'var']], 1, low, 2, medium, high]
}

/** The zones' paint until they are shown: their level's blue at no opacity, which then fades in. */
function hiddenPaint(map: MapLibreMap) {
  return {
    'fill-color': fillColor(map.getContainer()),
    'fill-opacity': 0,
    'fill-opacity-transition': { duration: CROSSFADE_MS, delay: 0 },
  }
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
      paint: hiddenPaint(map),
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

/* While a Metro Manila city is open or found, the map draws only its zones, from its own file
   (src/noah_cities.py), and the national tiles are hidden: MapLibre fetches and draws none of them. */

/** The province of the cities with a file of their own: NOAH's Metro Manila maps cover NCR's 17 only. */
const CITY_FILES_PROVINCE = 'National Capital Region'

/** A city whose zones alone are shown, by its PSGC and the name the legend writes. */
export type ZonesCity = { psgc: string; name: string }

/** The city `psgc` if it has a file of its own (null: none, or not in Metro Manila). */
export function zonesCity(cities: Cities, psgc: string | null): ZonesCity | null {
  const city = cities.features.find((feature) => feature.properties.psgc === psgc)?.properties
  return city?.province === CITY_FILES_PROVINCE ? { psgc: city.psgc, name: shortName(city) } : null
}

/** The source and layer of one city's zones, which share the id. */
const CITY_FLOOD = 'noah-city'

/** The zones of city `psgc` on NOAH's map for `period`. */
function cityUrl(period: FloodPeriod, psgc: string) {
  return `/data/noah_cities/${period}yr/${psgc}.json`
}

/** The city file each map draws, and what stops listening for its errors. */
const cityShown = new WeakMap<MapLibreMap, { url: string; stop: () => void }>()

/** Adds the zones in the file `url`, hidden. A file that does not load is removed, so Try again fetches it again. */
function addCityFlood(map: MapLibreMap, url: string) {
  map.addSource(CITY_FLOOD, { type: 'geojson', data: url, attribution: CREDIT })
  map.addLayer(
    {
      id: CITY_FLOOD,
      type: 'fill',
      source: CITY_FLOOD,
      layout: { visibility: 'none' },
      paint: hiddenPaint(map),
    },
    SLOTS.flood,
  )
  const onError = (event: MapEventType['error']) => {
    if (isSourceError(event, CITY_FLOOD)) {
      removeCityFlood(map)
    }
  }
  map.on('error', onError)
  cityShown.set(map, { url, stop: () => map.off('error', onError) })
}

/** Removes the city's zones, if the map has them. */
function removeCityFlood(map: MapLibreMap) {
  const shown = cityShown.get(map)
  if (!shown) {
    return
  }
  shown.stop()
  cityShown.delete(map)
  map.removeLayer(CITY_FLOOD)
  map.removeSource(CITY_FLOOD)
}

/** Shows NOAH's map for `period` (null: none) and hides the others; with `city`, only that city's zones. */
function showFlood(
  map: MapLibreMap,
  period: FloodPeriod | null,
  city: string | null,
  onStatus: (status: FloodStatus) => void,
): () => void {
  const national = period !== null && city === null ? floodId(period) : null
  if (period !== null && national && !map.getLayer(national)) {
    addFlood(map, period)
  }
  for (const other of FLOOD_PERIODS) {
    const id = floodId(other)
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, 'visibility', id === national ? 'visible' : 'none')
      map.setPaintProperty(id, 'fill-opacity', id === national ? FLOOD_OPACITY : 0)
    }
  }
  const url = period !== null && city !== null ? cityUrl(period, city) : null
  if (cityShown.get(map)?.url !== url) {
    removeCityFlood(map)
    if (url) {
      addCityFlood(map, url)
    }
  }
  if (url) {
    map.setLayoutProperty(CITY_FLOOD, 'visibility', 'visible')
    map.setPaintProperty(CITY_FLOOD, 'fill-opacity', FLOOD_OPACITY)
  }
  const shown = national ?? (url ? CITY_FLOOD : null)
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
 * Shows NOAH's map for `period` on `map` (null: none) and says how it is doing. With `city` (a PSGC
 * from zonesCity), only that city's zones are drawn.
 */
export function useFloodZones(
  map: MapLibreMap | null,
  period: FloodPeriod | null,
  city: string | null,
): { status: FloodStatus; retry: () => void } {
  const [news, setNews] = useState<{ key: string; status: FloodStatus } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const key = `${period}/${city}` // The status heard is for this map and city only
  useEffect(() => {
    if (!map) {
      return
    }
    return showFlood(map, period, city, (status) => setNews({ key: `${period}/${city}`, status }))
  }, [map, period, city, attempt])
  const status = period === null ? 'off' : news?.key === key ? news.status : 'loading'
  return { status, retry: () => setAttempt((count) => count + 1) }
}
