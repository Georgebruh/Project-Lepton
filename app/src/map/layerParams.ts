import { BASE_MAPS, type BaseMap } from './basemap.ts'

/*
 * F13: the map layers chosen in the Layers panel live in the address, like ?date= and ?lead=,
 * so a link opens the same map: ?base=satellite or ?base=terrain (the street map, the default,
 * is left out). levelSearch (routes.ts) keeps them when the reader moves between the levels.
 */
export const LAYER_PARAMS = { base: 'base' }

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
