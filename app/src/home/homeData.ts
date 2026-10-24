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

/** The numbers Home shows, from the files in public/data/. */

/** The storm and forecast Home previews. */
export const PREVIEW_STORM = 'kristine_2024'
export const PREVIEW_NAME = 'Kristine'
export const PREVIEW_LEAD = '1'

/** One forecast of the prophylaxis plan: what Home's map preview and its stock totals show. */
export type PlanPreviewData = {
  storm: Storm
  run: StormRun
  /** The flood the plan shows (1 day, w = 0.5, the PLAN_FLOOD): Quezon City's people and units. */
  flood: Flood
  shapes: BarangayShapes
  /** Each barangay's numbers in the run, by PSGC; all 142 join the shapes (joinRun). */
  barangays: Map<string, BarangayRun>
  /** The health centers C7 stocks, the largest doxycycline need first. */
  needs: CenterNeed[]
  /** The barangay of the health center first in that list, outlined on the map. */
  selected: string | undefined
  /** The map's five classes of share (storms.json). */
  classes: ShareClass[]
}

/** A storm's name without its month, as a sentence writes it. */
export function stormTitle(storm: Storm): string {
  return storm.name.split(', ')[0]
}

/** Loads the preview's files. */
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

/** Loads city_forecast.json, the forecasts, for the chart. */
export function loadCityForecast(): Promise<CityForecast> {
  return fetchJson<CityForecast>('/data/city_forecast.json')
}

/** What a loader gave: its value, "failed" (the error is in the console), or undefined while it loads. */
export type Loaded<T> = T | 'failed' | undefined

/** Runs `load` once, when the page opens. */
export function useLoaded<T>(load: () => Promise<T>): Loaded<T> {
  const [loaded, setLoaded] = useState<Loaded<T>>(undefined)
  useEffect(() => {
    let current = true // False once the page closes: a late answer is dropped
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
