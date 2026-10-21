import { SIMULATED_LABEL, formatCount, formatDayMonth, formatWeek, thresholdCount } from '../map/forecast.ts'
import type { ForecastWeek } from '../map/mapData.ts'
import { RANGE_MODEL, modelStyle } from './models.ts'
import type { StormMark } from './periods.ts'

/**
 * F9: what the chart says about one week, in its tooltip and, as one sentence, to a screen
 * reader moving from week to week with the arrow keys. Plain functions, no React.
 */

/** The series the chart shows besides the models' lines (Figma's Show toggles, node 12:989). */
export type Layers = { range: boolean; threshold: boolean; observed: boolean }

/** One line of a week's readout: its number, then what it is (dataviz: values lead, labels follow). */
export type ReadoutRow = {
  /** The series: a model's name, or "observed" or "threshold" (SeriesKey draws its key). */
  series: string
  value: string
  label: string
  /** Words after the label: the 90% range of M4's forecast, or that the count crossed the threshold. */
  note?: string
}

/** A week as the tooltip titles it: "Week 43 · 20–26 Oct 2024" (Figma's "Week 42 · 13–19 Oct 2026"). */
export function weekTitle(week: ForecastWeek): string {
  return `Week ${week.week} · ${formatWeek(week.start, week.end)}`
}

/**
 * The week's numbers for what the chart shows, in the key's order: each model's forecast for the
 * week (made the week before, rounded to whole cases as the city panel shows it; M4 with its
 * range), then the count and the epidemic threshold as a whole count (B7's rule).
 */
export function readoutRows(week: ForecastWeek, models: string[], layers: Layers, rangeName: string): ReadoutRow[] {
  const rows: ReadoutRow[] = models.map((model) => {
    const forecast = week.forecasts[model]
    const range = model === RANGE_MODEL && layers.range ? `${rangeName} range ${forecast.low}–${forecast.high}` : undefined
    return { series: model, value: formatCount(forecast.mu), label: `${modelStyle(model).key} forecast`, note: range }
  })
  if (layers.observed) {
    rows.push({ series: 'observed', value: formatCount(week.y), label: 'cases' })
  }
  if (layers.threshold) {
    const note = week.breached ? 'the count is above it' : undefined
    rows.push({ series: 'threshold', value: formatCount(thresholdCount(week.threshold)), label: 'epidemic threshold', note })
  }
  return rows
}

/** A storm's line in the readout of the week its flood began: "Kristine: flooding began 24 Oct". */
export function stormWords(storm: StormMark): string {
  return `${storm.label}: flooding began ${formatDayMonth(storm.start)}`
}

/**
 * The readout as one sentence, read out as the keyboard moves (the tooltip itself is hidden from
 * screen readers). A range's dash is read as "to": "90% range 22 to 58".
 */
export function readoutSentence(week: ForecastWeek, rows: ReadoutRow[], storm: StormMark | undefined, simulated: boolean): string {
  const parts = rows.map((row) => `${row.label} ${row.value}${row.note ? `, ${row.note.replace('–', ' to ')}` : ''}`)
  const words = [`${weekTitle(week).replace(' · ', ', ')}: ${parts.join('; ')}.`]
  if (storm) {
    words.push(`${stormWords(storm)}.`)
  }
  if (simulated) {
    words.push(`${SIMULATED_LABEL}.`)
  }
  return words.join(' ')
}
