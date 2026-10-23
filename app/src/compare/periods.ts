import { addDays, formatDayMonth, weekStart } from '../map/forecast.ts'
import type { CityForecast, ForecastWeek } from '../map/mapData.ts'
import type { Storm } from '../map/planData.ts'

/**
 * F9: the chart's three periods (Figma's Period tabs, node 12:996): the latest 12 weeks, one
 * calendar year, or the whole backtest, and what the x axis needs for each. Plain functions,
 * no React.
 *
 * The period is kept in the address: /compare?period=12w, ?period=2024 or ?period=all. Without
 * one, or with a year the backtest does not hold, the chart shows the latest year.
 *
 * Weeks are CDC/MMWR weeks, Sunday to Saturday, numbered by city_forecast.json's continuous
 * week_index. A year's axis spans all its weeks, also those the backtest has no forecast for
 * (the first two of 2018, the last of 2026), so each year's season sits in the same place.
 */

export type Period = { kind: 'recent' } | { kind: 'year'; year: number } | { kind: 'all' }

/** How many weeks the "12 weeks" tab shows: the latest in the backtest. */
export const RECENT_WEEKS = 12

/** The address's words for the two periods that are not a year. */
const RECENT_PARAM = '12w'
const ALL_PARAM = 'all'

const DAY_MS = 24 * 60 * 60 * 1000
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** The first and last week index the x axis spans. */
export type Span = { first: number; last: number }

/** A label under the x axis, at a week's index. */
export type Tick = { index: number; label: string }

/** A storm's flood marked on the chart, at the week flooding began (A11's start_date). */
export type StormMark = { storm: string; label: string; index: number; start: string }

/** The years the backtest has forecasts for, oldest first. */
export function backtestYears(forecast: CityForecast): number[] {
  return [...new Set(forecast.weeks.map((week) => week.year))].sort((a, b) => a - b)
}

/** The period in the address's ?period=; the latest year when it names none the backtest holds. */
export function parsePeriod(text: string | null, years: number[]): Period {
  if (text === RECENT_PARAM) {
    return { kind: 'recent' }
  }
  if (text === ALL_PARAM) {
    return { kind: 'all' }
  }
  const year = Number(text)
  return { kind: 'year', year: years.includes(year) ? year : years[years.length - 1] }
}

/** A period as the address writes it: "12w", "2024" or "all". */
export function periodParam(period: Period): string {
  if (period.kind === 'recent') {
    return RECENT_PARAM
  }
  return period.kind === 'all' ? ALL_PARAM : String(period.year)
}

/** The backtest's years in words: "2018–2026". */
export function allYearsName(years: number[]): string {
  return `${years[0]}–${years[years.length - 1]}`
}

/** Years as runs, as D8's figures write them: [2018, 2019, 2022, ..., 2026] is "2018–2019 and 2022–2026". */
export function yearsWords(years: number[]): string {
  const runs: number[][] = []
  for (const year of [...years].sort((a, b) => a - b)) {
    const run = runs[runs.length - 1]
    if (run && year === run[run.length - 1] + 1) {
      run.push(year)
    } else {
      runs.push([year])
    }
  }
  const words = runs.map((run) => (run.length === 1 ? String(run[0]) : `${run[0]}–${run[run.length - 1]}`))
  return words.length > 1 ? `${words.slice(0, -1).join(', ')} and ${words[words.length - 1]}` : words[0]
}

/** The period as the chart's title ends: "last 12 weeks", "2024" or "2018–2026". */
export function periodName(period: Period, years: number[]): string {
  if (period.kind === 'recent') {
    return `last ${RECENT_WEEKS} weeks`
  }
  return period.kind === 'all' ? allYearsName(years) : String(period.year)
}

/** The weeks of the backtest the period holds, oldest first. */
export function periodWeeks(forecast: CityForecast, period: Period): ForecastWeek[] {
  if (period.kind === 'recent') {
    return forecast.weeks.slice(-RECENT_WEEKS)
  }
  if (period.kind === 'year') {
    return forecast.weeks.filter((week) => week.year === period.year)
  }
  return forecast.weeks
}

/** The days from `from` to `to`, both YYYY-MM-DD. */
function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / DAY_MS)
}

/** The week index of the week that starts on `sunday`, counted from the backtest's first week. */
export function weekIndexOf(forecast: CityForecast, sunday: string): number {
  const first = forecast.weeks[0]
  return first.week_index + daysBetween(first.start, sunday) / 7
}

/** The Sunday that starts the week with index `index`. */
export function weekStartOf(forecast: CityForecast, index: number): string {
  const first = forecast.weeks[0]
  return addDays(first.start, 7 * (index - first.week_index))
}

/**
 * The Sunday that starts MMWR week 1 of `year`: the week holding 4 January, the first week with
 * at least four days in the year (CDC's rule, as epiweeks counts it).
 */
function firstSunday(year: number): string {
  return weekStart(`${year}-01-04`)
}

/** The week indexes the x axis spans: the period's weeks, or for a year all of its 52 or 53 weeks. */
export function periodSpan(forecast: CityForecast, period: Period, weeks: ForecastWeek[]): Span {
  if (period.kind === 'year') {
    return {
      first: weekIndexOf(forecast, firstSunday(period.year)),
      last: weekIndexOf(forecast, firstSunday(period.year + 1)) - 1,
    }
  }
  return { first: weeks[0].week_index, last: weeks[weeks.length - 1].week_index }
}

/**
 * The x axis's labels: each week's Sunday for the latest 12 weeks ("4 Oct"), the months of a
 * year (at the week holding the 1st; January at week 1), the years of the whole backtest.
 */
export function periodTicks(forecast: CityForecast, period: Period, span: Span, years: number[]): Tick[] {
  if (period.kind === 'recent') {
    return Array.from({ length: span.last - span.first + 1 }, (_, i) => {
      const index = span.first + i
      return { index, label: formatDayMonth(weekStartOf(forecast, index)) }
    })
  }
  if (period.kind === 'year') {
    return MONTHS.map((label, month) => {
      const first = `${period.year}-${String(month + 1).padStart(2, '0')}-01`
      return { index: Math.max(span.first, weekIndexOf(forecast, weekStart(first))), label }
    })
  }
  return years.map((year) => ({ index: Math.max(span.first, weekIndexOf(forecast, firstSunday(year))), label: String(year) }))
}

/**
 * A storm's name as the chart labels it: the part before the comma, without the kind of storm.
 * "Severe Tropical Storm Kristine, October 2024" is "Kristine"; "July 2025 floods" stays.
 */
export function stormLabel(storm: Storm): string {
  return storm.name.split(', ')[0].replace(/^(Super Typhoon|Typhoon|Severe Tropical Storm|Tropical Storm) /, '')
}

/** The storms whose flood began inside the span, each at the week it began, oldest first. */
export function stormsIn(forecast: CityForecast, storms: Storm[], span: Span): StormMark[] {
  return storms
    .map((storm) => ({
      storm: storm.storm,
      label: stormLabel(storm),
      index: weekIndexOf(forecast, weekStart(storm.start_date)),
      start: storm.start_date,
    }))
    .filter((mark) => mark.index >= span.first && mark.index <= span.last)
    .sort((a, b) => a.index - b.index)
}
