import { BASE_MAPS, type BaseMap } from './basemap.ts'
import { FLOOD_PERIODS, type FloodPeriod } from './floodLayer.ts'

/*
 * F13: the map layers chosen in the Layers panel live in the address, like ?date= and ?lead=,
 * so a link opens the same map: ?base=satellite or ?base=terrain (the street map, the default,
 * is left out), and ?flood=5, 25 or 100 for NOAH's flood zones (left out when they are off).
 * levelSearch (routes.ts) keeps them when the reader moves between the levels.
 */
export const LAYER_PARAMS = { base: 'base', flood: 'flood' }

/** The base map the address names; the street map if it names none, or one the app does not know. */
export function baseOf(params: URLSearchParams): BaseMap {
  const value = params.get(LAYER_PARAMS.base)
  return BASE_MAPS.find((base) => base === value) ?? 'map'
}

/** Writes `base` into `params` (the street map, the default, as no setting at all). */
export function setBaseParam(params: URLSearchParams, base: BaseMap): URLSearchParams {
  if (base === 'map') {
    params.delete(LAYER_PARAMS.base)
  } else {
    params.set(LAYER_PARAMS.base, base)
  }
  return params
}

/** The NOAH map the address names, by its rain's return period; null (no flood zones) if it names none the app has. */
export function floodOf(params: URLSearchParams): FloodPeriod | null {
  const value = Number(params.get(LAYER_PARAMS.flood))
  return FLOOD_PERIODS.find((period) => period === value) ?? null
}

/** Writes the NOAH map `period` into `params` (no flood zones, the default, as no setting at all). */
export function setFloodParam(params: URLSearchParams, period: FloodPeriod | null): URLSearchParams {
  if (period === null) {
    params.delete(LAYER_PARAMS.flood)
  } else {
    params.set(LAYER_PARAMS.flood, String(period))
  }
  return params
}
