import type { StyleSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { fetchBaseStyle } from './basemap.ts'
import type { Islands } from './borders.ts'

/** The files the map screens read. */

/** One city's or municipality's properties in ph_cities.json. */
export type CityProperties = {
  /** The 10-digit PSGC, e.g. "1381300000": every number joins on it. */
  psgc: string
  /** The name as PSA writes it, e.g. "City of Marikina". */
  name: string
  /** The province it lies in ("National Capital Region" for Metro Manila's 17). */
  province: string
  /** Whether the city has weekly case counts, so a forecast (only Quezon City so far). */
  has_data: boolean
  /** Where the map writes the city's name: only a city with data has one. */
  label_lon: number | null
  label_lat: number | null
}

export type Cities = FeatureCollection<Polygon | MultiPolygon, CityProperties>

/** A city's name as the map writes it, without PSA's "City of": "City of Marikina" is "Marikina". */
export function shortName(city: CityProperties): string {
  return city.name.replace(/^City of /, '')
}

/** One model's forecast for one week, from. */
export type ModelForecast = {
  /** The expected count. */
  mu: number
  /** The 90% range: the 5% and 95% quantiles. */
  low: number
  high: number
  /** The chance the count ends above the epidemic threshold, Pr(breach). */
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
  y: number | null
  /** The epidemic threshold T_w: a week breaches when its count is strictly above it. */
  threshold: number
  /** Null where y is. */
  breached: boolean | null
  forecasts: Record<string, ModelForecast>
  /** A week from city_simulation.json. */
  simulated?: boolean
}

export type OutbreakLevel = 'low' | 'watch' | 'high'

/** city_forecast.json. */
export type CityForecast = {
  /** True until the real counts are in: every Layer 1 number keeps the amber badge. */
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

/** city_simulation.json, the Simulation mode's weeks. */
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

/** The map's two modes, the Simulation | Real data buttons. */
export type DataMode = 'simulation' | 'real'

/** The forecast the map shows in a mode. */
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
  /** The islands' coastlines. */
  islands: Islands
  forecast: CityForecast
  /** The Simulation mode's weeks, or null if the file is missing (the map then has Real data only). */
  simulation: Simulation | null
  /** The street map's style, or null if it did not load (the map then draws on a plain background). */
  baseStyle: StyleSpecification | null
}

/** Fetch one of the files; a missing one stops with an error, which ErrorPage shows. */
export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`${path}: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

/** city_simulation.json, or null when it is missing. */
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

/** The /map route's loader. */
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
