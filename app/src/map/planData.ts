import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { fetchJson } from './mapData.ts'

/** The files the prophylaxis plan reads. */

/** The three units. */
export type Units = {
  /** Doxycycline 100 mg capsules, adults. */
  doxy100: number
  /** Children's courses (doxycycline 4 mg/kg once, or an alternative; by weight). */
  courses: number
  /** Amoxicillin 500 mg tablets, pregnant women. */
  amox500: number
}

/** One flood of a run, keyed "D1" (D = 1 day at w = 0.5) or "D7" (7 days). */
export type Flood = Units & {
  key: string
  /** The flood in words, e.g. "D = 1, w = 0.5". */
  flood: string
  D: number
  /** The share of exposed adults at moderate risk; null where it does not matter (D of 2 days or more). */
  w: number | null
  exposed: number
}

/** One run of a storm: the rain that fell. */
export type StormRun = {
  run: string
  /** The run's barangay file, under /data/. */
  file: string
  rain_product: string
  /** Whose return levels the rain is placed on: IMERG's for observed rain, ERA5's for forecasts. */
  levels_product: string
  /** How many days before its rain window the forecast was made; null for the observed run. */
  lead_days: number | null
  /** The day the forecast was made, YYYY-MM-DD; null for the observed run. */
  issued: string | null
  /** The 3-day rain window, YYYY-MM-DD. */
  window: { start: string; end: string }
  rain_mm: number
  levels_mm: Record<string, number>
  levels_years: number
  /** Where the rain falls against the return levels: "below R0", "R0 to R(5)", ..., "above R(100)". */
  position: string
  ei_pct: number
  /** How many barangays are flagged: flag_share or more of their residents in zones the rain floods. */
  flagged: number
  floods: Flood[]
}

/** A storm of storms.json, or a day's plan from a year file, in the same form. */
export type Storm = {
  /** The storm's key, e.g. "kristine_2024". */
  storm: string
  /** Its name in words, e.g. "Severe Tropical Storm Kristine, October 2024", or "Daily plan, 22–24 Jul 2024". */
  name: string
  /** The days it flooded Quezon City, YYYY-MM-DD, and how many. */
  start_date: string
  end_date: string
  D: number | null
  runs: StormRun[]
}

/** One of the map's five classes. */
export type ShareClass = { class: number; label: string; from: number; to: number }

/** How each unit per person is counted (config.py), as the barangay report explains. */
export type CountingRules = {
  doxy100_low: number
  doxy100_moderate: number
  doxy100_high_per_week: number
  amox500_pregnant: number
  week_days: number
  high_risk_days: number
}

/** storms.json. */
export type StormsFile = {
  /** "Stock-planning figures, not prescriptions: ..." */
  label: string
  source: string
  units: Record<keyof Units, string>
  /** The units per person. */
  counting: CountingRules
  /** A barangay is flagged when this share of its residents or more is exposed (0.25). */
  flag_share: number
  classes: ShareClass[]
  storms: Storm[]
}

export type BarangayProperties = {
  /** The 10-digit PSGC, e.g. "1381300121": every number joins on it. */
  psgc: string
  name: string
}

/** qc_barangays.geojson. */
export type BarangayShapes = FeatureCollection<Polygon | MultiPolygon, BarangayProperties>

/** One barangay in a run's file. */
export type BarangayRun = {
  psgc: string
  name: string
  /** Its 2024 residents. */
  pop_2024: number
  /** Its residents exposed: in zones the run's rain floods. */
  exposed: number
  /** Exposed / pop_2024, from 0 to 1: the measure behind its class and its flag. */
  share: number
  /** Its map class, 0 to 4: --color-data-ramp-1 to -5. */
  class: number
  flagged: boolean
  /** Its units per flood key ("D1", "D7"). */
  units: Record<string, Units>
}

/** barangays/<storm>_<run>.json. */
export type RunFile = { label: string; source: string; storm: string; run: string; barangays: BarangayRun[] }

/** One health center in centers.json. */
export type Center = {
  facility_code: string
  /** As the registry writes it, in capitals: "TATALON HEALTH CENTER". */
  name: string
  type: string
  lat: number | null
  lon: number | null
  psgc: string
  /** Its barangay's name, as on the map. */
  barangay: string
  /** Whether it gets stock; if not, `left_out` says why. */
  gets_stock: boolean
  left_out: string | null
}

/** One health center that holds part of a barangay's stock. */
export type BarangayCenter = {
  facility_code: string
  /** How the barangay's need reaches this center: its own, split by nearest residents, or the nearest. */
  rule: 'own' | 'split' | 'nearest'
  /** The share of the barangay's need it holds; a barangay's shares add up to 1. */
  share: number
  /** For rule nearest, the km from the barangay's centroid to the center; null otherwise. */
  km: number | null
}

/** centers.json. */
export type CentersFile = {
  label: string
  source: string
  units: Record<keyof Units, string>
  centers: Center[]
  /** needs[storm][run][flood key][facility_code]: a center's units, each rounded up to whole units. */
  needs: Record<string, Record<string, Record<string, Record<string, Units>>>>
  /** Each barangay's health centers by its PSGC, the largest share first. */
  barangay_centers: Record<string, BarangayCenter[]>
}

/** days/<year>.json, a year of daily plans. */
export type DaysFile = {
  label: string
  source: string
  /** The day the plans were made, and the UTC day ECMWF's archive was fetched. */
  made_on: string
  fetched_utc: string
  /** The first and last day with a plan, the same in every year's file. */
  first: string
  last: string
  year: number
  units: Record<keyof Units, string>
  /** Each day's plan, in date order, as storms.json writes a storm. */
  days: Storm[]
  /** needs[day key][run][flood key][facility_code], for the runs that expose anyone. */
  needs: CentersFile['needs']
}

export type PlanData = {
  storms: StormsFile
  centers: CentersFile
  shapes: BarangayShapes
}

let planFiles: Promise<PlanData> | null = null

/** The plan route's loader (router.tsx). */
export function loadPlanData(): Promise<PlanData> {
  if (!planFiles) {
    planFiles = Promise.all([
      fetchJson<StormsFile>('/data/storms.json'),
      fetchJson<CentersFile>('/data/centers.json'),
      fetchJson<BarangayShapes>('/data/qc_barangays.geojson'),
    ]).then(([storms, centers, shapes]) => ({ storms, centers, shapes }))
    planFiles.catch(() => {
      planFiles = null
    })
  }
  return planFiles
}

const runFiles = new Map<string, Promise<RunFile>>()

/** One run's barangay file. */
export function loadRun(file: string): Promise<RunFile> {
  let found = runFiles.get(file)
  if (!found) {
    found = fetchJson<RunFile>(`/data/${file}`)
    found.catch(() => runFiles.delete(file))
    runFiles.set(file, found)
  }
  return found
}

const dayFiles = new Map<number, Promise<DaysFile>>()

/** A year's daily plans (days/<year>.json), fetched once and kept, as the date moves back and forth. */
export function loadDays(year: number): Promise<DaysFile> {
  let found = dayFiles.get(year)
  if (!found) {
    found = fetchJson<DaysFile>(`/data/days/${year}.json`)
    found.catch(() => dayFiles.delete(year))
    dayFiles.set(year, found)
  }
  return found
}
