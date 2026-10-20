import { fetchJson, type CityForecast } from '../map/mapData.ts'
import type { Storm, StormsFile } from '../map/planData.ts'

/**
 * F9: the files Compare models reads, written by F2 (python -m src.app_data) into
 * public/data/, and the /compare route's loader that fetches them:
 *
 *   city_forecast.json   B10's forecasts per target week; made-up counts while "simulated"
 *   scores.json          each model's scores (D1-D3) and D5's primary endpoint. F2 writes it
 *                        beside B10's real run only, so it is fetched only then: while the
 *                        forecasts are simulated, no score can reach the page
 *   storms.json          the storms' flood dates (A11), marked on the chart
 */

/** One model's scores in scores.json. */
export type ModelScores = {
  /** Mean absolute error, cases a week (D1), over the MAE window. */
  mae: number
  /** The MAE over the "same week last year" miss of 2016-2017 (D2). */
  mase: number
  /** Weighted interval score (D1), over the range-score window. */
  wis: number
  /** The share of weeks whose count fell inside the 90% range (D1), 0 to 1. */
  coverage_90: number
  /** Brier score of the chance of an outbreak, Pr(breach) (D3), 0 to 1. */
  brier: number
}

/** D5's primary endpoint: the mean of |error M4| - |error M3| with its 95% block-bootstrap interval. */
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
  /** The B10 file the scores come from; city_forecast.json names the same one. */
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

/** scores.json, or null when it is missing; any other failure stops with an error, which ErrorPage shows. */
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

/**
 * The /compare route's loader. Scores show only beside a real run they were made from: a
 * scores.json from another B10 file than city_forecast.json's is left out, and the page shows
 * "—" (nothing on the page may read as a real result that is not one).
 */
export async function loadCompareData(): Promise<CompareData> {
  const [forecast, stormsFile] = await Promise.all([
    fetchJson<CityForecast>('/data/city_forecast.json'),
    fetchJson<StormsFile>('/data/storms.json'),
  ])
  let scores = forecast.simulated ? null : await fetchScores()
  if (scores && scores.source !== forecast.source) {
    console.warn(`scores.json is from ${scores.source}, city_forecast.json from ${forecast.source}: rerun python -m src.app_data`)
    scores = null
  }
  return { forecast, storms: stormsFile.storms, scores }
}
