import type { StyleSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { fetchBaseStyle } from './basemap.ts'

/**
 * F4: the files the map screens read, written by F2 (python -m src.app_data) into
 * public/data/, and the /map route's loader that fetches them. React Router keeps what the
 * loader returns while the reader moves between the map's levels (router.tsx).
 */

/** One city's properties in ncr_cities.geojson. */
export type CityProperties = {
  /** The 10-digit PSGC, e.g. "1381300000": every number joins on it. */
  psgc: string
  /** The name as PSA writes it, e.g. "City of Marikina". */
  name: string
  /** Whether the city has weekly case counts, so a forecast (only Quezon City so far). */
  has_data: boolean
  /** Where the map writes the city's name; null for a city too small to label (Pateros). */
  label_lon: number | null
  label_lat: number | null
}

export type Cities = FeatureCollection<Polygon | MultiPolygon, CityProperties>

/** A city's name as the map writes it, without PSA's "City of": "City of Marikina" is "Marikina". */
export function shortName(city: CityProperties): string {
  return city.name.replace(/^City of /, '')
}

/** One model's forecast for one week, from B10. */
export type ModelForecast = {
  /** The expected count. */
  mu: number
  /** The 90% range: the 5% and 95% quantiles. */
  low: number
  high: number
  /** The chance the count ends above the epidemic threshold, Pr(breach) (B7). */
  p_breach: number
}

/** One target week of city_forecast.json: the week forecast, its count and each model's forecast. */
export type ForecastWeek = {
  week_index: number
  year: number
  week: number
  /** The week's Sunday and Saturday (CDC/MMWR weeks), YYYY-MM-DD. */
  start: string
  end: string
  /** The count that week (made-up while the file says simulated). */
  y: number
  /** The epidemic threshold T_w: a week breaches when its count is strictly above it. */
  threshold: number
  breached: boolean
  forecasts: Record<string, ModelForecast>
}

export type OutbreakLevel = 'low' | 'watch' | 'high'

/** city_forecast.json. */
export type CityForecast = {
  /** True until A13's counts arrive and B10 runs on them: every Layer 1 number keeps the amber badge. */
  simulated: boolean
  note: string | null
  source: string
  option: string
  g: number
  horizon_weeks: number
  models: string[]
  /** The model whose forecast the map and the city panel show (config.APP_LEVEL_MODEL, M4). */
  map_model: string
  /** Each outbreak level and the Pr(breach) it starts at, lowest first (config.APP_LEVELS). */
  levels: { level: OutbreakLevel; from: number }[]
  /** The quantiles of the range, [0.05, 0.95]. */
  range: [number, number]
  covid_years: number[]
  weeks: ForecastWeek[]
}

export type MapData = {
  cities: Cities
  forecast: CityForecast
  /** F13: the street map's style, or null if it did not load (the map then draws on a plain background). */
  baseStyle: StyleSpecification | null
}

/** Fetch one of F2's files; a missing one stops with an error, which ErrorPage shows. */
export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`${path}: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

/**
 * The /map route's loader: the city outlines, the city forecast and (F13) the street map's
 * style, fetched together. A missing data file stops with an error; a street map that does
 * not load does not.
 */
export async function loadMapData(): Promise<MapData> {
  const [cities, forecast, baseStyle] = await Promise.all([
    fetchJson<Cities>('/data/ncr_cities.geojson'),
    fetchJson<CityForecast>('/data/city_forecast.json'),
    fetchBaseStyle(),
  ])
  return { cities, forecast, baseStyle }
}
