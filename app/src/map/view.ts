import type { LngLatBoundsLike, PaddingOptions } from 'maplibre-gl'
import { shapeParts } from '../exposed/nearest.ts'
import type { Cities } from './mapData.ts'
import { panelCover } from './motion.ts'
import { QC_PSGC, type MapLevel } from './routes.ts'

/*
 * F4: what the camera shows at each level. F13 moved it here from CityMap.tsx: the map no
 * longer stops at Metro Manila, so the map's pin button (MapLayout) brings the same view back.
 */

/** Space kept around what the camera fits, in px (Figma: 28 around Metro Manila, 32 around Quezon City). */
const FIT_PADDING = { metro: 28, city: 32 }

/**
 * F13: the least height, in px, the open city keeps on a phone. Legends taller than the map left
 * above the sheet (NOAH's over the map's own) then cover part of the city instead of leaving the
 * camera no room to fit it (it would stay where it was, zoomed out).
 */
const MIN_CITY_HEIGHT = 120

/** The box around some cities' outlines: [[west, south], [east, north]]. */
function boundsOf(features: Cities['features']): [[number, number], [number, number]] {
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
export function viewFor(
  level: MapLevel,
  cities: Cities,
  container: HTMLElement,
  controls: HTMLElement | null,
): { bounds: LngLatBoundsLike; padding: PaddingOptions } {
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
