import { formatDayMonth, formatWeek } from './forecast.ts'
import type {
  BarangayRun,
  BarangayShapes,
  CentersFile,
  Flood,
  RunFile,
  ShareClass,
  Storm,
  StormRun,
  StormsFile,
  Units,
} from './planData.ts'

/** Reading the prophylaxis plan for the date and the forecast the reader picks. */

/** The flood the plan shows. */
export const PLAN_FLOOD = 'D1'

/** A storm's forecasts, the one made 1 day ahead first. Its observed run. */
export function forecastRuns(storm: Storm): StormRun[] {
  return storm.runs
    .filter((run) => run.lead_days !== null)
    .sort((a, b) => (a.lead_days ?? 0) - (b.lead_days ?? 0))
}

/** The dates a storm's forecasts are shown for. */
export function stormDates(storm: Storm): { first: string; last: string } | null {
  const runs = forecastRuns(storm)
  if (!runs.length) {
    return null
  }
  const made = runs.map((run) => run.issued ?? run.window.start).sort()
  const ends = [...runs.map((run) => run.window.end), storm.end_date].sort()
  return { first: made[0], last: ends[ends.length - 1] }
}

/** The storm whose forecasts are shown on a date, or undefined if there is none. */
export function stormOn(storms: Storm[], date: string): Storm | undefined {
  return storms.find((storm) => {
    const dates = stormDates(storm)
    return dates !== null && dates.first <= date && date <= dates.last
  })
}

/** The storms that have forecasts, the earliest first: the links shown on a date without one. */
export function stormsWithForecasts(storms: Storm[]): Storm[] {
  return storms.filter((storm) => stormDates(storm) !== null).sort((a, b) => stormDate(a).localeCompare(stormDate(b)))
}

/** The date a link to a storm opens. */
export function stormDate(storm: Storm): string {
  return forecastRuns(storm)[0].window.start
}

/** The forecast the address asks for (?lead=2), if the storm has one made that many days ahead. */
export function chosenRun(storm: Storm, lead: string | null): StormRun {
  const runs = forecastRuns(storm)
  return runs.find((run) => String(run.lead_days) === lead) ?? runs[0]
}

/** A forecast's lead time in words: "1 day ahead", "2 days ahead". */
export function leadWords(days: number): string {
  return days === 1 ? '1 day ahead' : `${days} days ahead`
}

/** A forecast's lead time as its chip writes it: "1 day ahead", "2 days", "3 days". */
export function leadLabel(days: number): string {
  return days === 1 ? leadWords(days) : `${days} days`
}

/** The flood the plan shows (PLAN_FLOOD) in a run; stops with an error if storms.json lacks it. */
export function planFlood(storm: Storm, run: StormRun): Flood {
  const flood = run.floods.find((each) => each.key === PLAN_FLOOD)
  if (!flood) {
    throw new Error(`storms.json: ${storm.storm}, ${run.run} has no ${PLAN_FLOOD} flood: rerun python -m src.app_data`)
  }
  return flood
}

/** The forecast's rain in the panel's words: "233 mm of rain over 22–24 Oct 2024" (whole mm). */
export function rainLine(run: StormRun): string {
  return `${Math.round(run.rain_mm)} mm of rain over ${formatWeek(run.window.start, run.window.end)}`
}

/** Where the rain falls against the return levels, in words. */
const POSITION_WORDS: Record<string, string> = {
  'below R0': 'too little rain to flood',
  'R0 to R(5)': 'less than a 5-year storm',
  'R(5) to R(25)': 'between a 5- and a 25-year storm',
  'R(25) to R(100)': 'between a 25- and a 100-year storm',
  'above R(100)': 'more than a 100-year storm',
}

/** Where a run's rain falls against the return levels, in words: "between a 5- and a 25-year storm". */
export function positionWords(run: StormRun): string {
  return POSITION_WORDS[run.position] ?? run.position
}

/** When the forecast was made and where its rain falls, in the panel's words. */
export function issuedLine(run: StormRun): string {
  return run.issued ? `Issued ${formatDayMonth(run.issued)} · ${positionWords(run)}` : positionWords(run)
}

/** A share of residents as a whole percentage: "63%"; a share above 0 but under 0.5% is "<1%". */
export function formatShare(share: number): string {
  if (share > 0 && share < 0.005) {
    return '<1%'
  }
  return `${Math.round(share * 100)}%`
}

/** A run's barangays by PSGC, once they join the map's shapes. */
export function joinRun(shapes: BarangayShapes, run: RunFile): Map<string, BarangayRun> {
  const byPsgc = new Map(run.barangays.map((barangay) => [barangay.psgc, barangay]))
  const joined = shapes.features.filter((feature) => byPsgc.has(feature.properties.psgc)).length
  const all = shapes.features.length
  if (joined !== all || byPsgc.size !== all || run.barangays.length !== all) {
    throw new Error(
      `${run.storm}, ${run.run}: ${joined} of ${all} barangays join on PSGC, and all must: ` +
        'rerun python -m src.app_data',
    )
  }
  return byPsgc
}

/** The barangays in the order the wave reaches them. */
export function waveOrder(barangays: Iterable<BarangayRun>): string[] {
  return [...barangays]
    .sort((a, b) => b.share - a.share || b.exposed - a.exposed || a.psgc.localeCompare(b.psgc))
    .map((barangay) => barangay.psgc)
}

/** A share as a whole percentage, without the % sign: 0.05 is 5. */
function percent(share: number): number {
  return Math.round(share * 100)
}

/** A class as the legend writes it: "<5%", "5–15%", "15–25%", "25–50%", "50%+". */
export function classLabel(share: ShareClass, classes: ShareClass[]): string {
  if (share.class === classes[0].class) {
    return `<${percent(share.to)}%`
  }
  if (share.class === classes[classes.length - 1].class) {
    return `${percent(share.from)}%+`
  }
  return `${percent(share.from)}–${percent(share.to)}%`
}

const DARKEST = ['', 'the darkest', 'the two darkest', 'the three darkest', 'the four darkest']

/** The flag in the legend's words: "Flagged: the two darkest, 25% or more". */
export function flagLine(classes: ShareClass[], flagShare: number): string {
  const flagged = classes.filter((share) => share.from >= flagShare).length
  return `Flagged: ${DARKEST[flagged] ?? `the ${flagged} darkest`}, ${percent(flagShare)}% or more`
}

/** Words written in lower case inside a health center's name. */
const LOWER_WORDS = new Set(['and', 'na'])

/** The registry's capitals in title case, every word kept. */
export function titleCase(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .map((word, i) => {
      const lower = word.toLowerCase()
      return i > 0 && LOWER_WORDS.has(lower) ? lower : lower.charAt(0).toUpperCase() + lower.slice(1)
    })
    .join(' ')
}

/** A health center's name as the panel writes it. */
export function centerName(name: string): string {
  const full = titleCase(name)
  return / super health center$/i.test(full) ? full : full.replace(/ health center$/i, '')
}

/** A health center and its need for one run and flood, in whole units (rounded up). */
export type CenterNeed = {
  facilityCode: string
  /** The registry's name, in capitals. */
  name: string
  barangay: string
  units: Units
}

/** The health centers that get stock. */
export function centerNeeds(centers: CentersFile, storm: string, run: string, flood: string): CenterNeed[] {
  const needs = centers.needs[storm]?.[run]?.[flood]
  if (!needs) {
    throw new Error(`centers.json has no need for ${storm}, ${run}, ${flood}: rerun python -m src.app_data`)
  }
  const listed = new Map(centers.centers.map((center) => [center.facility_code, center]))
  return Object.entries(needs)
    .map(([code, units]) => {
      const center = listed.get(code)
      if (!center) {
        throw new Error(
          `centers.json: health center ${code} has a need but is not in its list: rerun python -m src.app_data`,
        )
      }
      return { facilityCode: code, name: center.name, barangay: center.barangay, units }
    })
    .sort((a, b) => b.units.doxy100 - a.units.doxy100 || a.name.localeCompare(b.name))
}

/** The units of several centers added up. */
export function addUnits(needs: CenterNeed[]): Units {
  return needs.reduce(
    (sum, { units }) => ({
      doxy100: sum.doxy100 + units.doxy100,
      courses: sum.courses + units.courses,
      amox500: sum.amox500 + units.amox500,
    }),
    { doxy100: 0, courses: 0, amox500: 0 },
  )
}

/** One field of a CSV row, in quotes if it holds a comma, a quote or a line break. */
function csvField(value: string | number): string {
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

/** A date as the stock list (and the barangay report) writes it: "21 Oct 2024". */
export function fullDate(day: string): string {
  return `${formatDayMonth(day)} ${day.slice(0, 4)}`
}

/** The stock list the panel's Export button saves, as CSV. */
export function stockList(storms: StormsFile, centers: CentersFile, storm: Storm, run: StormRun): string {
  const flood = planFlood(storm, run)
  const needs = centerNeeds(centers, storm.storm, run.run, flood.key)
  const sum = addUnits(needs)
  const made = run.issued ? `Forecast made ${fullDate(run.issued)}, ${leadWords(run.lead_days ?? 1)}` : 'Rain that fell'
  const rows: (string | number)[][] = [
    [storms.label],
    [`LEPTON stock list for Quezon City's health centers: ${storm.name}`],
    [`${made}: ${rainLine(run)}, ${positionWords(run)} (on ${run.levels_product}'s return levels)`],
    [
      `Flood: ${flood.flood} (D: days flooded; w: the share of exposed adults with a wound ` +
        'or with water in the eyes, nose or mouth)',
    ],
    [
      "Each health center's units are rounded up to whole units, the level stock is ordered at, " +
        `so the ${needs.length} centers add up to a little more than Quezon City's totals, which ` +
        'are rounded to the nearest unit.',
    ],
    [],
    [
      'Facility code',
      'Health center',
      'Barangay',
      'Doxycycline 100 mg capsules (adults)',
      "Children's courses (dosed by weight)",
      'Amoxicillin 500 mg tablets (pregnant women)',
    ],
    ...needs.map((need) => [
      need.facilityCode,
      need.name,
      need.barangay,
      need.units.doxy100,
      need.units.courses,
      need.units.amox500,
    ]),
    ['', `All ${needs.length} health centers`, '', sum.doxy100, sum.courses, sum.amox500],
    ['', 'Quezon City, as on the panel', '', flood.doxy100, flood.courses, flood.amox500],
    [],
    ...centers.centers
      .filter((center) => !center.gets_stock)
      .map((center) => [
        `Not stocked: ${center.name} (${center.facility_code}, ${center.barangay}): ${center.left_out ?? 'left out'}`,
      ]),
  ]
  return rows.map((row) => row.map(csvField).join(',')).join('\r\n') + '\r\n'
}

/** The stock list's file name: "lepton-stock-list_kristine_2024_lead1.csv". */
export function stockListName(storm: Storm, run: StormRun): string {
  return `lepton-stock-list_${storm.storm}_lead${run.lead_days}.csv`
}
