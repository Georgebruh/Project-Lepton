import { useEffect, useState } from 'react'
import { fetchJson, type CityForecast } from '../map/mapData.ts'
import { centerNeeds, chosenRun, joinRun, planFlood, type CenterNeed } from '../map/plan.ts'
import {
  loadPlanData,
  loadRun,
  type BarangayRun,
  type BarangayShapes,
  type Flood,
  type ShareClass,
  type Storm,
  type StormRun,
} from '../map/planData.ts'

/**
 * F6: the numbers Home shows, from F2's files in public/data/. Home computes none of them: the
 * preview of the prophylaxis plan reads the same files as the map's level 3 (F5), through the
 * same loaders, so a reader who goes on to the map does not fetch them again.
 */

/**
 * The storm and forecast Home previews: Kristine, 1 day ahead (Figma's notes on Home), and the
 * storm's short name in Home's text ("Forecast 1 day before Kristine"). Change them together.
 */
export const PREVIEW_STORM = 'kristine_2024'
export const PREVIEW_NAME = 'Kristine'
export const PREVIEW_LEAD = '1'

/** One forecast of the prophylaxis plan: what Home's map preview and its stock totals show. */
export type PlanPreviewData = {
  storm: Storm
  run: StormRun
  /** The flood the plan shows (1 day, w = 0.5, F5's PLAN_FLOOD): Quezon City's people and units. */
  flood: Flood
  shapes: BarangayShapes
  /** Each barangay's numbers in the run, by PSGC; all 142 join the shapes (joinRun). */
  barangays: Map<string, BarangayRun>
  /** The health centers C7 stocks, the largest doxycycline need first. */
  needs: CenterNeed[]
  /** The barangay of the health center first in that list, outlined on the map (Figma: "Selected"). */
  selected: string | undefined
  /** The map's five classes of share (storms.json). */
  classes: ShareClass[]
}

/**
 * A storm's name without its month, as a sentence writes it: "Severe Tropical Storm Kristine,
 * October 2024" is "Severe Tropical Storm Kristine".
 */
export function stormTitle(storm: Storm): string {
  return storm.name.split(', ')[0]
}

/** Loads the preview's files: storms.json, centers.json, the barangay shapes and the run's barangay file. */
export async function loadPlanPreview(): Promise<PlanPreviewData> {
  const { storms, centers, shapes } = await loadPlanData()
  const storm = storms.storms.find((each) => each.storm === PREVIEW_STORM)
  if (!storm) {
    throw new Error(`storms.json has no ${PREVIEW_STORM}: rerun python -m src.app_data`)
  }
  const run = chosenRun(storm, PREVIEW_LEAD)
  const flood = planFlood(storm, run)
  const barangays = joinRun(shapes, await loadRun(run.file))
  const needs = centerNeeds(centers, storm.storm, run.run, flood.key)
  const first = centers.centers.find((center) => center.facility_code === needs[0]?.facilityCode)
  return { storm, run, flood, shapes, barangays, needs, selected: first?.psgc, classes: storms.classes }
}

/** Loads city_forecast.json, B10's forecasts (made-up counts until A13), for the chart. */
export function loadCityForecast(): Promise<CityForecast> {
  return fetchJson<CityForecast>('/data/city_forecast.json')
}

/** What a loader gave: its value, "failed" (the error is in the console), or undefined while it loads. */
export type Loaded<T> = T | 'failed' | undefined

/**
 * Runs `load` once, when the page opens. Unlike the map, Home does not stop with an error page
 * when a file is missing: the section says it could not load, and the rest of the page stands.
 */
export function useLoaded<T>(load: () => Promise<T>): Loaded<T> {
  const [loaded, setLoaded] = useState<Loaded<T>>(undefined)
  useEffect(() => {
    let current = true // false once the page closes: a late answer is dropped
    load().then(
      (value) => {
        if (current) {
          setLoaded(value)
        }
      },
      (error: unknown) => {
        console.error(error)
        if (current) {
          setLoaded('failed')
        }
      },
    )
    return () => {
      current = false
    }
  }, [load])
  return loaded
}
