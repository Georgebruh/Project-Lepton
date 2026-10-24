import type { CityForecast, DataMode, ForecastWeek, OutbreakLevel, Simulation } from './mapData.ts'

/** Reading Quezon City's forecast for the date the reader picks. */

/** Shown with every Layer 1 number while city_forecast.json says simulated. */
export const SIMULATED_LABEL = 'Simulated until QCESD data'

/** Shown with every number of a week from the Simulation mode. */
export const SIMULATION_LABEL = 'Simulated'

/** Whether a week's numbers are simulated: the whole file made up, or a week the Simulation mode added. */
export function isSimulated(forecast: CityForecast, week: ForecastWeek | undefined): boolean {
  return forecast.simulated || week?.simulated === true
}

/** The badge's words for simulated numbers. */
export function badgeWords(fileSimulated: boolean): string {
  return fileSimulated ? SIMULATED_LABEL : SIMULATION_LABEL
}

/** The badge a week's numbers carry when isSimulated. */
export function simulatedLabel(forecast: CityForecast): string {
  return badgeWords(forecast.simulated)
}

/** Each outbreak level's name, as the legend and the badges write it. */
export const LEVEL_NAMES: Record<OutbreakLevel, string> = { low: 'Low', watch: 'Watch', high: 'High' }

/** Each level's badge tone. */
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

/** The dates the picker offers. */
export function dateRange(forecast: CityForecast): { first: string; last: string } {
  const lead = 7 * forecast.horizon_weeks
  const weeks = forecast.weeks
  return { first: addDays(weeks[0].start, -lead), last: addDays(weeks[weeks.length - 1].start, -lead + 6) }
}

/** Today's date where the reader is, YYYY-MM-DD. */
export function today(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

/** The date the map shows. */
export function chosenDate(forecast: CityForecast, requested: string | null): string {
  const { first, last } = dateRange(forecast)
  const day = requested && isDay(requested) ? requested : today()
  return day < first ? first : day > last ? last : day
}

/** The forecast made in the week holding `day`, for the week after it. */
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

/** Pr(breach) as the panel writes it, a whole percentage: "22%". */
export function formatChance(p: number): string {
  if (p < 0.005) {
    return '<1%'
  }
  if (p >= 0.995) {
    return '>99%'
  }
  return `${Math.round(p * 100)}%`
}

/** The outbreak level of a chance of an outbreak. */
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

/** The epidemic threshold as a whole count. */
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

/** What a data mode shows, in one sentence: whose counts, to when, and (simulated) which rain. In the info pop-up. */
export function dataNote(mode: DataMode, simulation: Simulation | null, realEnd: string): string {
  return mode === 'simulation' && simulation
    ? `QCESD's counts to ${formatDay(simulation.last_real_week.end)}, then made up. This week's rain: ` +
        `ECMWF's forecast of ${formatDay(simulation.weather.fetched_on)}.`
    : `QCESD's counts and LEPTON's forecasts, to ${formatDay(realEnd)}.`
}

/** A date as day and month, for a year the reader already sees. */
export function formatDayMonth(day: string): string {
  const date = utc(day)
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`
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
