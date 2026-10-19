import type { CityForecast, ForecastWeek, OutbreakLevel } from './mapData.ts'

/**
 * F4: reading Quezon City's forecast for the date the reader picks. Plain functions, no React.
 *
 * Dates are YYYY-MM-DD strings, and weeks are CDC/MMWR weeks, Sunday to Saturday, as everywhere
 * in LEPTON. The date picks the forecast day: the week that holds it. The panel shows the
 * forecast made that week for the week after it, "next week", as Figma frame 2 does: Tue 22 Oct
 * 2024 shows the week of 27 Oct – 2 Nov 2024.
 */

/** Shown with every Layer 1 number while city_forecast.json says simulated (app check U2). */
export const SIMULATED_LABEL = 'Simulated until QCESD data'

/** Each outbreak level's name, as the legend and the badges write it. */
export const LEVEL_NAMES: Record<OutbreakLevel, string> = { low: 'Low', watch: 'Watch', high: 'High' }

/** Each level's badge tone (Design notes: teal for the calm end, amber for warnings, red for alerts). */
export const LEVEL_TONES: Record<OutbreakLevel, 'accent' | 'warn' | 'alert'> = {
  low: 'accent',
  watch: 'warn',
  high: 'alert',
}

const DAY_MS = 24 * 60 * 60 * 1000
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** A YYYY-MM-DD date as a Date at midnight UTC. */
function utc(day: string): Date {
  return new Date(`${day}T00:00:00Z`)
}

/** Whether a string is a real YYYY-MM-DD date (2024-02-30 is not). */
function isDay(text: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return false
  }
  const date = utc(text)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === text
}

/** The date `days` days after `day` (before it, if `days` is negative). */
export function addDays(day: string, days: number): string {
  return new Date(utc(day).getTime() + days * DAY_MS).toISOString().slice(0, 10)
}

/** The Sunday that starts the MMWR week holding `day`. */
export function weekStart(day: string): string {
  return addDays(day, -utc(day).getUTCDay())
}

/**
 * The dates the picker offers: from the Sunday of the first week a forecast was made to the
 * Saturday of the last. A forecast for week t was made horizon_weeks (1) weeks before it.
 */
export function dateRange(forecast: CityForecast): { first: string; last: string } {
  const lead = 7 * forecast.horizon_weeks
  const weeks = forecast.weeks
  return { first: addDays(weeks[0].start, -lead), last: addDays(weeks[weeks.length - 1].start, -lead + 6) }
}

/**
 * The date the map shows: the one in the address, moved inside the backtest's dates if it
 * falls outside them; the latest date if the address names none, or no real date.
 */
export function chosenDate(forecast: CityForecast, requested: string | null): string {
  const { first, last } = dateRange(forecast)
  if (!requested || !isDay(requested)) {
    return last
  }
  return requested < first ? first : requested > last ? last : requested
}

/** The forecast made in the week holding `day`, for the week after it; undefined if the backtest has none. */
export function forecastFor(forecast: CityForecast, day: string): ForecastWeek | undefined {
  const target = addDays(weekStart(day), 7 * forecast.horizon_weeks)
  return forecast.weeks.find((week) => week.start === target)
}

/** The `count` weeks just before `week` that the backtest has, oldest first: the panel's bars. */
export function weeksBefore(forecast: CityForecast, week: ForecastWeek, count: number): ForecastWeek[] {
  return forecast.weeks.filter(
    (other) => other.week_index >= week.week_index - count && other.week_index < week.week_index,
  )
}

/**
 * Pr(breach) as the panel writes it, a whole percentage: "22%". Under 0.5% it reads "<1%" and
 * from 99.5% ">99%", because an outbreak is never certain either way.
 */
export function formatChance(p: number): string {
  if (p < 0.005) {
    return '<1%'
  }
  if (p >= 0.995) {
    return '>99%'
  }
  return `${Math.round(p * 100)}%`
}

/**
 * The outbreak level of a chance of an outbreak: the highest level whose starting chance it
 * reaches (city_forecast.json's levels, set in config.py). The chance is first rounded to a
 * whole percent, as the panel writes it, so a chance shown as "10%" never reads Low.
 */
export function levelOf(p: number, levels: CityForecast['levels']): OutbreakLevel {
  const percent = Math.round(p * 100)
  let level = levels[0].level
  for (const step of levels) {
    if (percent >= Math.round(step.from * 100)) {
      level = step.level
    }
  }
  return level
}

/**
 * The epidemic threshold as a whole count. A week breaches when its count is strictly above
 * T_w, which for whole counts means above T_w rounded down (B7: Pr(breach) = sf(floor(T_w))).
 */
export function thresholdCount(threshold: number): number {
  return Math.floor(threshold)
}

/** The width of the forecast range, from city_forecast.json's quantiles: [0.05, 0.95] is "90%". */
export function rangePercent(forecast: CityForecast): string {
  return `${Math.round((forecast.range[1] - forecast.range[0]) * 100)}%`
}

/** A count with thousands separators: 1,234. */
export function formatCount(count: number): string {
  return Math.round(count).toLocaleString('en-US')
}

/** A date as the date picker writes it: "Tue 22 Oct 2024". */
export function formatDay(day: string): string {
  const date = utc(day)
  return `${WEEKDAYS[date.getUTCDay()]} ${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`
}

/** A week's dates: "27 Oct – 2 Nov 2024", "4–10 Oct 2026" within one month, both years across New Year. */
export function formatWeek(start: string, end: string): string {
  const [a, b] = [utc(start), utc(end)]
  const [dayA, dayB] = [a.getUTCDate(), b.getUTCDate()]
  const [monthA, monthB] = [MONTHS[a.getUTCMonth()], MONTHS[b.getUTCMonth()]]
  const [yearA, yearB] = [a.getUTCFullYear(), b.getUTCFullYear()]
  if (yearA !== yearB) {
    return `${dayA} ${monthA} ${yearA} – ${dayB} ${monthB} ${yearB}`
  }
  if (monthA !== monthB) {
    return `${dayA} ${monthA} – ${dayB} ${monthB} ${yearB}`
  }
  return `${dayA}–${dayB} ${monthB} ${yearB}`
}
