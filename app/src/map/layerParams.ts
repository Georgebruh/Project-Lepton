import { BASE_MAPS, type BaseMap } from './basemap.ts'
import { FLOOD_PERIODS, type FloodPeriod } from './floodLayer.ts'
import type { DataMode } from './mapData.ts'
import { WEATHER, type Weather } from './weather.ts'

/*
 * F13: the map layers chosen in the Layers panel live in the address, like ?date= and ?lead=,
 * so a link opens the same map: ?base=satellite or ?base=terrain (the street map, the default,
 * is left out), ?flood=5, 25 or 100 for NOAH's flood zones, ?view=3d for the 3D view, and
 * ?wx=clouds, radar, rain, rain-day or photo-day for the weather layer (each left out when off).
 * F14: ?data=real for the Real data mode (Simulation, the default, is left out).
 * levelSearch (routes.ts) keeps them when the reader moves between the levels.
 */
export const LAYER_PARAMS = { base: 'base', flood: 'flood', view: 'view', weather: 'wx', data: 'data' }

/** F14: the mode the address names: Real data with ?data=real, otherwise Simulation, the default. */
export function dataOf(params: URLSearchParams): DataMode {
  return params.get(LAYER_PARAMS.data) === 'real' ? 'real' : 'simulation'
}

/** F14: writes the mode into `params` (Simulation, the default, as no setting at all). */
export function setDataParam(params: URLSearchParams, mode: DataMode): URLSearchParams {
  if (mode === 'real') {
    params.set(LAYER_PARAMS.data, 'real')
  } else {
    params.delete(LAYER_PARAMS.data)
  }
  return params
}

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

/** Whether the address asks for the 3D view (?view=3d). */
export function is3D(params: URLSearchParams): boolean {
  return params.get(LAYER_PARAMS.view) === '3d'
}

/** Writes the 3D view into `params` (the flat map, the default, as no setting at all). */
export function set3DParam(params: URLSearchParams, on: boolean): URLSearchParams {
  if (on) {
    params.set(LAYER_PARAMS.view, '3d')
  } else {
    params.delete(LAYER_PARAMS.view)
  }
  return params
}

/** The weather layer the address names; null (none) if it names none the app has. */
export function weatherOf(params: URLSearchParams): Weather | null {
  const value = params.get(LAYER_PARAMS.weather)
  return WEATHER.find((kind) => kind === value) ?? null
}

/** Writes the weather layer `kind` into `params` (none, the default, as no setting at all). */
export function setWeatherParam(params: URLSearchParams, kind: Weather | null): URLSearchParams {
  if (kind === null) {
    params.delete(LAYER_PARAMS.weather)
  } else {
    params.set(LAYER_PARAMS.weather, kind)
  }
  return params
}
