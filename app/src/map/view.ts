import type { EaseToOptions, Map as MapLibreMap } from 'maplibre-gl'
import { shapeParts } from '../exposed/nearest.ts'
import maplibregl from '../lib/maplibre.ts'
import type { Cities } from './mapData.ts'
import { panelCover } from './motion.ts'
import { QC_PSGC, type MapLevel } from './routes.ts'

/* What the camera shows at each level. */

/** Space kept around what the camera fits, in px. */
const FIT_PADDING = { country: 28, city: 32 }

/** The least height, in px, the open city keeps on a phone. */
const MIN_CITY_HEIGHT = 120

/** MapLibre's whole world at zoom 0, in px: one 512 px tile. */
const WORLD_PX = 512

/** How many zoom levels the camera steps back when the city panel closes: twice the ground each way. */
const CLOSE_ZOOM_OUT = 1

/** A box on the map: [[west, south], [east, north]]. */
type Box = [[number, number], [number, number]]

/** What a level shows: the box to fit, and the room to keep around it on each side, in px. */
export type LevelView = { bounds: Box; padding: { top: number; bottom: number; left: number; right: number } }

/** The box around some cities' outlines. */
function boundsOf(features: Cities['features']): Box {
  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const { geometry } of features) {
    for (const [lon, lat] of shapeParts(geometry).flat(2)) {
      west = Math.min(west, lon)
      east = Math.max(east, lon)
      south = Math.min(south, lat)
      north = Math.max(north, lat)
    }
  }
  return [
    [west, south],
    [east, north],
  ]
}

/** The box around every city and municipality, computed once per file: the Philippines. */
const countryBounds = new WeakMap<Cities, Box>()

/** What the camera shows at a level. */
export function viewFor(
  level: MapLevel,
  cities: Cities,
  container: HTMLElement,
  controls: HTMLElement | null,
  topBar: HTMLElement | null = null,
): LevelView {
  if (level === 1) {
    const pad = FIT_PADDING.country
    if (!countryBounds.has(cities)) {
      countryBounds.set(cities, boundsOf(cities.features))
    }
    return { bounds: countryBounds.get(cities)!, padding: { top: pad, bottom: pad, left: pad, right: pad } }
  }
  const pad = FIT_PADDING.city
  const open = cities.features.filter((feature) => feature.properties.psgc === QC_PSGC)
  const cover = panelCover(container.clientWidth, container.clientHeight)
  const most = container.clientHeight - 2 * pad - MIN_CITY_HEIGHT
  const bottom = cover.bottom > 0 ? Math.max(cover.bottom, Math.min(cover.bottom + (controls?.offsetHeight ?? 0), most)) : 0
  // And the top left corner's logo and data modes, while the city keeps at least MIN_CITY_HEIGHT
  const top = Math.max(0, Math.min(topBar?.offsetHeight ?? 0, most - bottom))
  return { bounds: boundsOf(open), padding: { top: pad + top, bottom: pad + bottom, left: pad + cover.left, right: pad } }
}

/** What the camera shows of a city the map's search found (MapSearch), at level 1. */
export function cityView(
  cities: Cities,
  psgc: string,
  container: HTMLElement,
  controls: HTMLElement | null,
  topBar: HTMLElement | null,
): LevelView {
  const pad = FIT_PADDING.city
  const city = cities.features.filter((feature) => feature.properties.psgc === psgc)
  const most = container.clientHeight - 2 * pad - MIN_CITY_HEIGHT
  const bottom = Math.max(0, Math.min(controls?.offsetHeight ?? 0, most))
  const top = Math.max(0, Math.min(topBar?.offsetHeight ?? 0, most - bottom))
  return { bounds: boundsOf(city), padding: { top: pad + top, bottom: pad + bottom, left: pad, right: pad } }
}

/** The camera, for easeTo, when the city panel closes (its Close button, or the browser's Back). */
export function closeCamera(map: MapLibreMap, view: LevelView, pitch: number): EaseToOptions {
  return { center: map.getCenter(), zoom: map.getZoom() - CLOSE_ZOOM_OUT, padding: view.padding, pitch, bearing: 0 }
}

/** The event data a camera move hands MapLibre. */
export const LEVEL_FIT = { levelFit: true }
export const READER_MOVE = { readerMove: true }

/** The camera, for easeTo, that shows a level's view tilted by `pitch` (0 flat), facing north. */
export function levelCamera(view: LevelView, container: HTMLElement, pitch: number): EaseToOptions | null {
  const { top, bottom, left, right } = view.padding
  const width = container.clientWidth - left - right
  const height = container.clientHeight - top - bottom
  if (width <= 0 || height <= 0) {
    return null
  }
  const [[west, south], [east, north]] = view.bounds
  const yNorth = maplibregl.MercatorCoordinate.fromLngLat([west, north]).y
  const ySouth = maplibregl.MercatorCoordinate.fromLngLat([west, south]).y
  const scale = Math.min(width / (((east - west) / 360) * WORLD_PX), height / ((ySouth - yNorth) * WORLD_PX))
  return {
    center: [(west + east) / 2, new maplibregl.MercatorCoordinate(0.5, (yNorth + ySouth) / 2).toLngLat().lat],
    zoom: Math.log2(scale),
    padding: view.padding,
    pitch,
    bearing: 0,
  }
}

/** Moves the camera to a level's view tilted by `pitch`. */
export function moveToLevel(
  map: MapLibreMap,
  view: LevelView,
  pitch: number,
  motion: Pick<EaseToOptions, 'duration' | 'easing'>,
): boolean {
  const camera = levelCamera(view, map.getContainer(), pitch)
  if (camera) {
    map.easeTo({ ...camera, ...motion }, LEVEL_FIT)
  }
  return camera !== null
}
