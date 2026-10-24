import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { fetchJson } from './mapData.ts'

/**
 * F5: the files the prophylaxis plan reads, written by F2 (python -m src.app_data) into
 * public/data/, and the plan route's loader that fetches them. Every dose figure in them is
 * stock planning, not a prescription; each file says so in its `label`.
 *
 *   storms.json             each storm's runs: the rain, where it falls against the return
 *                           levels, the barangays flagged, and QC's residents exposed and units
 *   qc_barangays.geojson    the 142 barangay shapes, joined to every number on the PSGC
 *   centers.json            the health centers, each run's need per center and (F15) the
 *                           centers that hold each barangay's stock
 *   barangays/<storm>_<run>.json   one per run: each barangay's numbers, fetched only when shown
 *
 * F16 adds a plan for every day, written by python -m src.app_days, each year fetched only when
 * the chosen date is in it (loadDays):
 *
 *   days/<year>.json        each day's plan in storms.json's form, and its runs' needs per center
 *   barangays/days/<date>_<run>.json   one per run that exposes anyone
 *   barangays/days/no_flood.json       the one file every run that exposes nobody points to
 */

/** The three units, as C6 counts them. */
export type Units = {
  /** Doxycycline 100 mg capsules, adults. */
  doxy100: number
  /** Children's courses (doxycycline 4 mg/kg once, or an alternative; by weight). */
  courses: number
  /** Amoxicillin 500 mg tablets, pregnant women. */
  amox500: number
}

/** One flood of a run, keyed "D1" (D = 1 day at w = 0.5) or "D7" (7 days); QC's residents exposed and units. */
export type Flood = Units & {
  key: string
  /** The flood in words, e.g. "D = 1, w = 0.5". */
  flood: string
  D: number
  /** The share of exposed adults at moderate risk; null where it does not matter (D of 2 days or more). */
  w: number | null
  exposed: number
}

/** One run of a storm: the rain that fell (run "observed") or a forecast 1, 2 or 3 days ahead ("lead 1"). */
export type StormRun = {
  run: string
  /** The run's barangay file, under /data/. */
  file: string
  rain_product: string
  /** Whose return levels the rain is placed on: IMERG's for observed rain, ERA5's for forecasts (rule 3). */
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

/**
 * A storm of storms.json, or (F16) a day's plan from a year file, in the same form: then the key
 * is "day_2024-07-22", the dates are its 3-day rain window and D is null.
 */
export type Storm = {
  /** The storm's key, e.g. "kristine_2024". */
  storm: string
  /** Its name in words, e.g. "Severe Tropical Storm Kristine, October 2024", or "Daily plan, 22–24 Jul 2024". */
  name: string
  /** The days it flooded Quezon City (A11), YYYY-MM-DD, and how many (D; null for a day's plan). */
  start_date: string
  end_date: string
  D: number | null
  runs: StormRun[]
}

/** One of the map's five classes: barangays whose share of residents exposed runs from `from` up to `to`. */
export type ShareClass = { class: number; label: string; from: number; to: number }

/**
 * F15: how C6 counts each unit per person (config.py), which the barangay report explains: the
 * capsules per adult at low and moderate risk, per high-risk adult and week of flooding (weeks of
 * `week_days`, rounded up), and the tablets per pregnant woman. A flood of `high_risk_days` or
 * longer makes every exposed adult high risk. Children get one course per week of flooding, at
 * least one.
 */
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
  /** F15: C6's units per person. */
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
  /** Its 2024 residents (C1). */
  pop_2024: number
  /** Its residents exposed: in zones the run's rain floods. */
  exposed: number
  /** exposed / pop_2024, from 0 to 1: the measure behind its class and its flag. */
  share: number
  /** Its map class, 0 to 4: --color-data-ramp-1 to -5. */
  class: number
  flagged: boolean
  /** Its units per flood key ("D1", "D7"). */
  units: Record<string, Units>
}

/** barangays/<storm>_<run>.json. */
export type RunFile = { label: string; source: string; storm: string; run: string; barangays: BarangayRun[] }

/** One health center in centers.json (A10's registry). */
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
  /** Whether C7 sends it stock; if not, `left_out` says why. */
  gets_stock: boolean
  left_out: string | null
}

/**
 * F15: one health center that holds part of a barangay's stock, as C7 sends the barangay's need
 * (centers.json's barangay_centers).
 */
export type BarangayCenter = {
  facility_code: string
  /**
   * own: the barangay's one health center. split: one of its several centers, which takes the
   * share of its residents who live nearest it. nearest: a barangay without one sends all of its
   * need to the nearest center.
   */
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
  /** F15: each barangay's health centers by its PSGC, the largest share first. */
  barangay_centers: Record<string, BarangayCenter[]>
}

/**
 * F16: days/<year>.json, a year of daily plans. A day's plan is for the 3 days of rain from that
 * day: the forecasts made 1 to 3 days before it (ECMWF, from February 2024), or before the archive
 * the rain that fell (IMERG). Most days' rain floods nobody, and their plan needs no stock.
 */
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
  /** needs[day key][run][flood key][facility_code], for the runs that expose anyone; the others need nothing. */
  needs: CentersFile['needs']
}

export type PlanData = {
  storms: StormsFile
  centers: CentersFile
  shapes: BarangayShapes
}

let planFiles: Promise<PlanData> | null = null

/**
 * The plan route's loader (router.tsx): storms.json, centers.json and the barangay shapes,
 * fetched together the first time the plan opens and kept for the next time. A failed fetch is
 * tried again then; this time it stops with an error, which ErrorPage shows.
 */
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

/**
 * One run's barangay file (`file` as storms.json names it), fetched once and kept, since the
 * lead chips go back and forth between runs.
 */
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

/** F16: a year's daily plans (days/<year>.json), fetched once and kept, as the date moves back and forth. */
export function loadDays(year: number): Promise<DaysFile> {
  let found = dayFiles.get(year)
  if (!found) {
    found = fetchJson<DaysFile>(`/data/days/${year}.json`)
    found.catch(() => dayFiles.delete(year))
    dayFiles.set(year, found)
  }
  return found
}
