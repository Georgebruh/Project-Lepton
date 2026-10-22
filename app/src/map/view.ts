import type { EaseToOptions, Map as MapLibreMap } from 'maplibre-gl'
import { shapeParts } from '../exposed/nearest.ts'
import maplibregl from '../lib/maplibre.ts'
import type { Cities } from './mapData.ts'
import { panelCover } from './motion.ts'
import { QC_PSGC, type MapLevel } from './routes.ts'

/*
 * F4: what the camera shows at each level. F13 moved it here from CityMap.tsx: the map no
 * longer stops at Metro Manila, so the map's pin button (MapLayout) brings the same view back.
 *
 * F13: the camera moves to a level's view with easeTo (moveToLevel, levelCamera), so the view
 * keeps the 3D view's tilt, and the view's padding stays the camera's own: the camera then zooms,
 * turns and tilts about the middle of the map left in sight, beside the panel or above the sheet.
 */

/** Space kept around what the camera fits, in px (Figma: 28 around Metro Manila, 32 around Quezon City). */
const FIT_PADDING = { metro: 28, city: 32 }

/**
 * F13: the least height, in px, the open city keeps on a phone. Legends taller than the map left
 * above the sheet (NOAH's over the map's own) then cover part of the city instead of leaving the
 * camera no room to fit it (it would stay where it was, zoomed out).
 */
const MIN_CITY_HEIGHT = 120

/** MapLibre's whole world at zoom 0, in px: one 512 px tile. */
const WORLD_PX = 512

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

/**
 * What the camera shows at a level: all of Metro Manila at level 1; the open city at levels 2
 * and 3, kept clear of the panel by padding the side it covers: the right by the panel's width,
 * or on a phone the bottom by the sheet's height and by `controls`, the legend and zoom buttons
 * that stand on it (F11, panelCover), leaving the city at least MIN_CITY_HEIGHT. `container`
 * is the map's element, at its size now.
 */
export function viewFor(level: MapLevel, cities: Cities, container: HTMLElement, controls: HTMLElement | null): LevelView {
  if (level === 1) {
    const pad = FIT_PADDING.metro
    return { bounds: boundsOf(cities.features), padding: { top: pad, bottom: pad, left: pad, right: pad } }
  }
  const pad = FIT_PADDING.city
  const open = cities.features.filter((feature) => feature.properties.psgc === QC_PSGC)
  const cover = panelCover(container.clientWidth, container.clientHeight)
  const most = container.clientHeight - 2 * pad - MIN_CITY_HEIGHT
  const bottom = cover.bottom > 0 ? Math.max(cover.bottom, Math.min(cover.bottom + (controls?.offsetHeight ?? 0), most)) : 0
  return { bounds: boundsOf(open), padding: { top: pad, bottom: pad + bottom, left: pad, right: pad + cover.right } }
}

/**
 * F13: the event data a camera move hands MapLibre, which its movestart event carries, so CityMap
 * can tell whether the reader has moved the map away from the level's view: a move to the level's
 * view (moveToLevel) carries LEVEL_FIT, and the zoom buttons' READER_MOVE (MapLibre gives them
 * no event of the reader's to tell by).
 */
export const LEVEL_FIT = { levelFit: true }
export const READER_MOVE = { readerMove: true }

/**
 * F13: the camera, for easeTo, that shows a level's view tilted by `pitch` (0 flat), facing north:
 * the zoom at which the box just fits in the map left in sight, as fitBounds finds it, and the
 * box's middle in the middle of the map left in sight. The padding goes to the camera, which
 * keeps that middle there at any tilt. fitBounds' own way of shifting the middle holds only while
 * the map is not tilted (on a phone, a tilt would throw the city off the top of the strip above
 * the sheet). Heights down the flat map are MapLibre's
 * MercatorCoordinate y, 0 at the world's top to 1 at its bottom. Null if the map is too small
 * to fit the box.
 */
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

/**
 * F13: moves the camera to a level's view tilted by `pitch` (levelCamera), with `motion`
 * (duration and easing; not marked essential, so with reduced motion MapLibre jumps). False if
 * the map is too small to fit the view, and the camera stays where it is.
 */
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
