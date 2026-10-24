import { fetchJson, type CityForecast } from '../map/mapData.ts'
import type { Storm, StormsFile } from '../map/planData.ts'

/** The files Compare models reads. */

/** One model's scores in scores.json. */
export type ModelScores = {
  /** Mean absolute error, cases a week, over the MAE window. */
  mae: number
  /** The MAE over the "same week last year" miss of 2016-2017. */
  mase: number
  /** Weighted interval score, over the range-score window. */
  wis: number
  /** The share of weeks whose count fell inside the 90% range, 0 to 1. */
  coverage_90: number
  /** Brier score of the chance of an outbreak, Pr(breach), 0 to 1. */
  brier: number
}

/** The primary endpoint: the mean of |error M4| - |error M3| with its 95% block-bootstrap interval. */
export type PrimaryResult = {
  /** "M4 vs M3" (config.PRIMARY_COMPARISON). */
  comparison: string
  /** The bootstrap's block length in weeks (8). */
  block_weeks: number
  /** How many target weeks the mean is over. */
  weeks: number
  mean_diff: number
  low: number
  high: number
  /** The interval in words: "M4 misses less", "M3 misses less" or "no clear difference". */
  verdict: string
}

/** scores.json. */
export type Scores = {
  /** The forecasts file the scores come from; city_forecast.json names the same one. */
  source: string
  /** The years each score is over: MAE and MASE, then WIS, 90% coverage and the Brier score. */
  windows: { mae_mase: number[]; wis_coverage_brier: number[] }
  models: Record<string, ModelScores>
  primary: PrimaryResult
}

export type CompareData = {
  forecast: CityForecast
  storms: Storm[]
  /** The real run's scores; null while the forecasts are simulated, so the page shows "—". */
  scores: Scores | null
}

/** scores.json, or null when it is missing. */
async function fetchScores(): Promise<Scores | null> {
  const res = await fetch('/data/scores.json')
  if (res.status === 404) {
    console.warn('/data/scores.json is missing beside a real run: rerun python -m src.app_data')
    return null
  }
  if (!res.ok) {
    throw new Error(`/data/scores.json: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as Scores
}

/** The scores to show beside `forecast`: only those made from the same real run. */
export function scoresFor(forecast: CityForecast, scores: Scores | null): Scores | null {
  if (forecast.simulated || !scores) {
    return null
  }
  if (scores.source !== forecast.source) {
    console.warn(`scores.json is from ${scores.source}, city_forecast.json from ${forecast.source}: rerun python -m src.app_data`)
    return null
  }
  return scores
}

/** The loader of Compare models, now a tab of the map's city panel (/map/quezon-city/compare). */
export async function loadCompareData(): Promise<Omit<CompareData, 'forecast'>> {
  const [stormsFile, scores] = await Promise.all([fetchJson<StormsFile>('/data/storms.json'), fetchScores()])
  return { storms: stormsFile.storms, scores }
}
