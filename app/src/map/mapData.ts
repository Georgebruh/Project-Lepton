import type { StyleSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { fetchBaseStyle } from './basemap.ts'
import type { Islands } from './borders.ts'

/**
 * F4: the files the map screens read, written by F2 (python -m src.app_data) into
 * public/data/, and the /map route's loader that fetches them. React Router keeps what the
 * loader returns while the reader moves between the map's levels (router.tsx).
 *
 * F14: the map shows every city and municipality of the Philippines (ph_cities.json), and its
 * Simulation mode adds city_simulation.json's weeks (python -m src.app_simulation) after the
 * real ones (withSimulation).
 */

/** One city's or municipality's properties in ph_cities.json. */
export type CityProperties = {
  /** The 10-digit PSGC, e.g. "1381300000": every number joins on it. */
  psgc: string
  /** The name as PSA writes it, e.g. "City of Marikina". */
  name: string
  /** F14: the province it lies in ("National Capital Region" for Metro Manila's 17). */
  province: string
  /** Whether the city has weekly case counts, so a forecast (only Quezon City so far). */
  has_data: boolean
  /** Where the map writes the city's name: only a city with data has one (F14: the street map names the rest). */
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
  /** The count that week (made-up while the file says simulated). F14: null for a simulated week that has not ended. */
  y: number | null
  /** The epidemic threshold T_w: a week breaches when its count is strictly above it. */
  threshold: number
  /** Null where y is. */
  breached: boolean | null
  forecasts: Record<string, ModelForecast>
  /** F14: a week from city_simulation.json: its count, if any, is made up, and its forecasts were made on made-up counts. */
  simulated?: boolean
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

/**
 * F14: city_simulation.json, the Simulation mode's weeks: QCESD's counts end at last_real_week,
 * and each week after it has a made-up count (the median of M4's forecast), up to the week
 * before this one, then forecasts to next week, made with ECMWF's rain forecast of `made_on`.
 */
export type Simulation = {
  label: string
  /** The day the simulation was made, the "today" it runs to, YYYY-MM-DD. */
  made_on: string
  /** The last week with a real count, and the Saturday it ends. */
  last_real_week: { week_index: number; end: string }
  /** The weather forecast the last weeks' rain comes from: the model and the day it was fetched. */
  weather: { model: string; fetched_on: string; weeks: number[] }
  weeks: ForecastWeek[]
}

/** F14: the map's two modes, the Simulation | Real data buttons: the real weeks with or without the simulated ones. */
export type DataMode = 'simulation' | 'real'

/**
 * F14: the forecast the map shows in a mode: in Simulation mode the real weeks, then the
 * simulation's (each marked simulated); in Real data mode the real weeks only. A simulation
 * week the real file also holds is left out, so a newer real run always wins.
 */
export function withSimulation(forecast: CityForecast, simulation: Simulation | null, mode: DataMode): CityForecast {
  if (mode === 'real' || !simulation) {
    return forecast
  }
  const last = forecast.weeks[forecast.weeks.length - 1].week_index
  const added = simulation.weeks.filter((week) => week.week_index > last).map((week) => ({ ...week, simulated: true }))
  return { ...forecast, weeks: [...forecast.weeks, ...added] }
}

export type MapData = {
  cities: Cities
  /** F14: the islands' coastlines (ph_islands.json), drawn between the country's view and the towns' borders (borders.ts). */
  islands: Islands
  forecast: CityForecast
  /** F14: the Simulation mode's weeks, or null if the file is missing (the map then has Real data only). */
  simulation: Simulation | null
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

/** F14: city_simulation.json, or null when it is missing; any other failure stops with an error, which ErrorPage shows. */
async function fetchSimulation(): Promise<Simulation | null> {
  const res = await fetch('/data/city_simulation.json')
  if (res.status === 404) {
    console.warn('/data/city_simulation.json is missing: run python -m src.app_simulation. The map shows real data only.')
    return null
  }
  if (!res.ok) {
    throw new Error(`/data/city_simulation.json: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as Simulation
}

/**
 * The /map route's loader: the city outlines, (F14) the islands' coastlines, the city forecast,
 * (F14) the simulation and (F13) the street map's style, fetched together. A missing outline or
 * forecast file stops with an error; a missing simulation or a street map that does not load
 * does not.
 */
export async function loadMapData(): Promise<MapData> {
  const [cities, islands, forecast, simulation, baseStyle] = await Promise.all([
    fetchJson<Cities>('/data/ph_cities.json'),
    fetchJson<Islands>('/data/ph_islands.json'),
    fetchJson<CityForecast>('/data/city_forecast.json'),
    fetchSimulation(),
    fetchBaseStyle(),
  ])
  return { cities, islands, forecast, simulation, baseStyle }
}
