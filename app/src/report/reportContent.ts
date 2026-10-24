import { formatKm, type LonLat } from '../exposed/nearest.ts'
import {
  LEVEL_NAMES,
  addDays,
  formatChance,
  formatCount,
  formatWeek,
  isSimulated,
  levelOf,
  rangePercent,
  simulatedLabel,
  thresholdCount,
  weekStart,
} from '../map/forecast.ts'
import type { CityForecast, ForecastWeek } from '../map/mapData.ts'
import {
  PLAN_FLOOD,
  classLabel,
  formatShare,
  fullDate,
  leadWords,
  planFlood,
  planRuns,
  positionWords,
  titleCase,
  waveOrder,
} from '../map/plan.ts'
import type {
  BarangayRun,
  BarangayShapes,
  CentersFile,
  CountingRules,
  Flood,
  Storm,
  StormRun,
  StormsFile,
  Units,
} from '../map/planData.ts'

/*
 * F15: what the barangay report says, for health offices and LGUs: one barangay's exposure and
 * stock for the storm forecast the map shows, its forecasts made 1 to 3 days ahead, the health
 * centers that hold its stock, Quezon City's case forecast, and how the figures were made.
 * Plain functions, no PDF and no React: reportPdf.ts draws this content.
 *
 * Every number is one of the app's files', written out as the map writes it (formatCount,
 * formatShare): storms.json, the runs' barangay files, centers.json and city_forecast.json.
 * Nothing is computed again here but the barangay's rank among the 142 and the units per person
 * the text explains (from storms.json's counting). Stock planning, not prescriptions.
 */

/** One forecast of the storm, with its barangays (its barangay file joined to the shapes). */
export type LeadRun = { run: StormRun; barangays: Map<string, BarangayRun> }

/** What the report is made from: the plan's files and the forecast the map shows. */
export type ReportInput = {
  storms: StormsFile
  centers: CentersFile
  shapes: BarangayShapes
  storm: Storm
  /** The forecast the map shows (the panel's lead chip). */
  run: StormRun
  /** Every forecast of the storm, the map's among them. */
  leads: LeadRun[]
  /** The barangay reported on. */
  psgc: string
  /** Quezon City's forecasts as the map has them (Simulation or Real data). */
  forecast: CityForecast
  /** The forecast made in the week of the map's date, for the week after it; undefined if there is none. */
  week: ForecastWeek | undefined
  /** The map's date, YYYY-MM-DD. */
  date: string
  /** The map's address, which opens this forecast again. */
  link: string
  /** When the report is made. */
  made: Date
}

/** A key figure: a number in large type, what it counts, and a line under that. */
export type Figure = { value: string; label: string; detail: string }

/** A table: its column heads and its rows of cells; a `strong` row is set in bold. */
export type Table = { heads: string[]; rows: { cells: string[]; strong?: boolean }[] }

export type ReportContent = {
  fileName: string
  /** The PDF's title, as a PDF reader shows it. */
  docTitle: string
  /** storms.json's label: stock-planning figures, not prescriptions (rule 10). */
  label: string
  name: string
  /** Under the name: the city, the PSGC and the barangay's 2024 residents. */
  about: string
  /** Whether the barangay is flagged: the chip's words ("Flagged", "Not flagged") and why. */
  flag: { flagged: boolean; label: string; text: string }
  /** The forecast's box: the storm, the rain forecast and the city's totals. */
  storm: string
  forecastLine: string
  cityLine: string
  figures: Figure[]
  figuresNote: string
  stock: { table: Table; notes: string[] }
  /** The forecasts made before the rain, or (F16) a day's rain that fell: the section's title, table and note. */
  leads: { title: string; table: Table; note: string }
  centers: {
    intro: string
    table: Table
    serves: string[]
    leftOut: string[]
    note: string
    /** Each center's pin on the map: its number in the table and its place. */
    pins: { number: number; at: LonLat }[]
  }
  map: {
    psgc: string
    /** Each barangay's class (0 to 4) in this forecast, by PSGC. */
    classes: Map<string, number>
    legend: { cls: number; label: string }[]
    caption: string
  }
  city: { title: string; lines: string[]; badge: string | null }
  method: string[]
  limits: string[]
  sources: string[]
  made: string
  link: string
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Why C7 leaves a health center out (centers.json's left_out), in the report's words. */
const LEFT_OUT_WORDS: Record<string, string> = {
  'no coordinates': 'the registry gives it no location',
  'point outside its barangay': 'its registered location lies outside its barangay',
}

/** What the figures cannot claim: the paper's limitations and How it works' limits, shortened. */
const LIMITS = [
  "Stock planning, not prescriptions. DOH DM 2023-0309 requires a physician's consultation before anyone takes prophylaxis.",
  'Full coverage: every exposed resident is counted, and every course taken. Scale the figures by the share of ' +
    'residents expected to come forward.',
  'Everyone in a flooded zone is counted as touching the water, at any depth. Who has a wound, or has swallowed ' +
    'floodwater, is not known: hence the share w.',
  'A forecast can miss. For the July 2025 floods, the forecasts made 1 to 3 days ahead put far fewer residents in ' +
    'flooded zones than the rain that fell did.',
  "NOAH's maps state no design rain duration, and the rain below which nobody counts as exposed (half the 5-year " +
    'rain) has not been tuned on past floods.',
  'These barangay figures have not been checked against barangay case counts: none were available. Lactating women ' +
    'are not counted apart, since DM 2023-0309 gives them no regimen.',
]

/** The sources of the figures, with their licences (the app's footer and How it works' Sources). */
const SOURCES = [
  'Flood hazard maps: Project NOAH, UP Resilience Institute (ODbL).',
  "Population: WorldPop 2024 (CC BY 4.0); PSA's 2024 census; PSA's 2020 census ages via OCHA (CC BY); PSA's 2024 " +
    'registered births (CC BY).',
  'Barangay boundaries: PSA and NAMRIA via OCHA (CC BY-IGO).',
  'Health centers: DOH National Health Facility Registry.',
  'Rain: ECMWF IFS forecasts and the ERA5 reanalysis via Open-Meteo (CC BY 4.0; ERA5 contains modified Copernicus ' +
    'Climate Change Service information); the rain that fell, GPM IMERG Late v07 (NASA GES DISC). River basins: ' +
    'HydroBASINS (Lehner and Grill, 2013).',
  'City case counts: Quezon City Epidemiology and Surveillance Division (weekly city totals only).',
  'Regimens: DOH Department Memorandum 2023-0309.',
]

/** A share as a whole percentage: 0.5 is "50%". */
function percent(share: number): string {
  return `${Math.round(share * 100)}%`
}

/** 1st, 2nd, 3rd, 4th, ... 11th, 12th, 13th, ... 21st. */
function ordinal(n: number): string {
  const teen = n % 100 >= 11 && n % 100 <= 13
  const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${suffix}`
}

/** Names as a sentence lists them: "A", "A and B", "A, B and C". */
function listWords(names: string[]): string {
  return names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** A name in a file name: lower case, no accents, words joined by hyphens ("Santo Niño" is "santo-nino"). */
function slug(name: string): string {
  return name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

/** When the report was made, in the reader's own time and offset: "23 Oct 2026, 22:45 (UTC+08:00)". */
function madeWords(when: Date): string {
  const two = (n: number) => String(n).padStart(2, '0')
  const offset = -when.getTimezoneOffset()
  const zone = `UTC${offset < 0 ? '-' : '+'}${two(Math.floor(Math.abs(offset) / 60))}:${two(Math.abs(offset) % 60)}`
  return (
    `${when.getDate()} ${MONTHS[when.getMonth()]} ${when.getFullYear()}, ` +
    `${two(when.getHours())}:${two(when.getMinutes())} (${zone})`
  )
}

/** A flood of a run in words: "1-day flood". */
function floodName(flood: Flood): string {
  return `${flood.D}-day flood`
}

/** Weeks of flooding, as C6 counts them: whole weeks, rounded up. */
function floodWeeks(flood: Flood, counting: CountingRules): number {
  return Math.ceil(flood.D / counting.week_days)
}

/** The report's file name, as the stock list names its CSV: "lepton-barangay-report_tatalon_kristine_2024_lead1.pdf". */
export function reportFileName(name: string, storm: Storm, run: StormRun): string {
  return `lepton-barangay-report_${slug(name)}_${storm.storm}_${run.run.replace(/\s+/g, '')}.pdf`
}

/** When a forecast was made: "21 Oct 2024, 1 day ahead"; for observed rain, its product. */
function issuedWords(run: StormRun): string {
  return run.issued && run.lead_days !== null
    ? `${fullDate(run.issued)}, ${leadWords(run.lead_days)}`
    : `the rain that fell (${run.rain_product})`
}

/** F16: what the report calls a run: "this forecast", or for the rain that fell (a day before ECMWF's archive) "this rain". */
function runName(run: StormRun): string {
  return run.lead_days === null ? 'this rain' : 'this forecast'
}

/** F16: what the report calls a run's rain: "this forecast's rain", or "this rain". */
function rainName(run: StormRun): string {
  return run.lead_days === null ? 'this rain' : "this forecast's rain"
}

/** A barangay's units in one flood of a run; stops with an error if its file lacks that flood. */
function unitsIn(barangay: BarangayRun, flood: Flood, run: StormRun): Units {
  const units = barangay.units[flood.key]
  if (!units) {
    throw new Error(`${run.file}: ${barangay.name} has no units for the flood ${flood.key}: rerun python -m src.app_data`)
  }
  return units
}

/** A barangay in one forecast; stops with an error if the forecast's file lacks it. */
function barangayIn(lead: LeadRun, psgc: string): BarangayRun {
  const barangay = lead.barangays.get(psgc)
  if (!barangay) {
    throw new Error(`${lead.run.file} has no barangay ${psgc}: rerun python -m src.app_data`)
  }
  return barangay
}

/** Whether a barangay is flagged, and why, for the line under its name. */
function flagText(barangay: BarangayRun, storms: StormsFile, run: StormRun): ReportContent['flag'] {
  const line = `barangays are flagged at ${percent(storms.flag_share)} or more`
  const share = `${formatShare(barangay.share)} of its residents live in zones ${rainName(run)} floods (${line}).`
  if (barangay.flagged) {
    return { flagged: true, label: 'Flagged', text: share }
  }
  return {
    flagged: false,
    label: 'Not flagged',
    text: barangay.exposed > 0 ? share : `None of its residents live in zones ${rainName(run)} floods.`,
  }
}

/** Quezon City's totals for the forecast, and the barangay's rank among the 142 by share exposed. */
function cityLine(input: ReportInput, lead: LeadRun, barangay: BarangayRun): string {
  const { storm, run, shapes } = input
  const flood = planFlood(storm, run)
  const all = shapes.features.length
  const totals =
    flood.exposed > 0
      ? `Across Quezon City ${runName(run)} puts ${formatCount(flood.exposed)} residents (${run.ei_pct.toFixed(1)}% of ` +
        `the city) in flooded zones and flags ${run.flagged} of ${all} barangays.`
      : `Across Quezon City ${runName(run)} puts no resident in a flooded zone and flags no barangay.`
  if (barangay.exposed === 0) {
    return totals
  }
  const rank = waveOrder(lead.barangays.values()).indexOf(barangay.psgc) + 1
  return `${totals} ${barangay.name} is ${ordinal(rank)} of the ${all} by the share of its residents exposed.`
}

/** The key figures for the map's flood: residents exposed and the three units. */
function figures(barangay: BarangayRun, units: Units): Figure[] {
  return [
    {
      value: formatCount(barangay.exposed),
      label: 'residents exposed',
      detail: `${formatShare(barangay.share)} of ${formatCount(barangay.pop_2024)}`,
    },
    { value: formatCount(units.doxy100), label: 'doxycycline 100 mg capsules', detail: 'for adults' },
    { value: formatCount(units.courses), label: "children's courses", detail: 'dosed by weight' },
    { value: formatCount(units.amox500), label: 'amoxicillin 500 mg tablets', detail: 'for pregnant women' },
  ]
}

/** Who each adult capsule is for in one flood, and how many each gets (C6's counting rules). */
function adultsIn(flood: Flood, counting: CountingRules): string {
  if (flood.w !== null) {
    return (
      `In a ${floodName(flood)}, ${percent(flood.w)} are at moderate risk (a wound, or floodwater in the eyes, nose ` +
      `or mouth), ${counting.doxy100_moderate} capsules each, and the rest at low risk, ${counting.doxy100_low} each.`
    )
  }
  const weeks = floodWeeks(flood, counting)
  return (
    `In a ${floodName(flood)}, every exposed adult is at high risk: ${counting.doxy100_high_per_week} capsules per ` +
    `week of flooding, ${counting.doxy100_high_per_week * weeks} each.`
  )
}

/**
 * The stock to prepare: a row per unit, who it is for and how it is counted, and a column per
 * flood of the forecast (a 1-day and a 7-day flood: a forecast cannot know how long it lasts).
 */
function stockSection(storms: StormsFile, run: StormRun, barangay: BarangayRun): ReportContent['stock'] {
  const { counting } = storms
  const columns = run.floods.map((flood) => unitsIn(barangay, flood, run))
  // Courses per child in each flood: one per week of flooding, at least one (C6)
  const perChild = run.floods.map((flood) => Math.max(1, floodWeeks(flood, counting)))
  const courseWords = perChild.every((n) => n === perChild[0])
    ? `${perChild[0]} each in ${run.floods.length > 1 ? 'either flood' : `a ${floodName(run.floods[0])}`}`
    : listWords(run.floods.map((flood, i) => `${perChild[i]} each in a ${floodName(flood)}`))
  const rows = [
    {
      cells: [
        'Doxycycline 100 mg capsules',
        `Exposed adults, not counting pregnant women. ${run.floods.map((flood) => adultsIn(flood, counting)).join(' ')}`,
        ...columns.map((units) => formatCount(units.doxy100)),
      ],
    },
    {
      cells: [
        "Children's courses",
        `Exposed children under 18: one course per week of flooding, at least one, so ${courseWords}. A course ` +
          'is doxycycline 4 mg/kg once (at most 200 mg) or an alternative; the pharmacy turns courses into tablets ' +
          'by weight.',
        ...columns.map((units) => formatCount(units.courses)),
      ],
    },
    {
      cells: [
        'Amoxicillin 500 mg tablets',
        `Exposed pregnant women: ${counting.amox500_pregnant} tablets each, or the same number of erythromycin ` +
          '250 mg tablets if allergic.',
        ...columns.map((units) => formatCount(units.amox500)),
      ],
    },
  ]
  const notes: string[] = []
  if (run.floods.length > 1) {
    notes.push(
      `${run.lead_days === null ? 'The rain alone' : 'A forecast made days ahead'} cannot tell how long the flood ` +
        `will last, so the stock is given for ${listWords(run.floods.map((flood) => `a ${flood.D}-day`))} flood.`,
    )
  }
  const [shortest, longest] = [columns[0], columns[columns.length - 1]]
  if (run.floods.length > 1 && longest.doxy100 < shortest.doxy100) {
    notes.push(
      'A longer flood needs fewer capsules: every exposed adult is then at high risk, counted at ' +
        `${counting.doxy100_high_per_week} capsules a week, while in a short flood each adult at moderate risk ` +
        `is counted at ${counting.doxy100_moderate}.`,
    )
  }
  notes.push(
    "The counts follow DOH DM 2023-0309's regimens; a physician decides each person's prophylaxis. Every exposed " +
      'resident is counted, and every course taken (full coverage). Rounded to whole units.',
  )
  return {
    table: { heads: ['Stock', 'Who it is for, and how it is counted', ...run.floods.map(floodName)], rows },
    notes,
  }
}

/**
 * The storm's forecasts, the earliest first, each with the barangay's exposure and its units for
 * the map's flood. F16: a day before ECMWF's archive has the rain that fell instead, one row.
 */
function leadSection(input: ReportInput): ReportContent['leads'] {
  const { storm, run, leads, psgc } = input
  const rows = planRuns(storm)
    .reverse()
    .map((each) => {
      const lead = leads.find((other) => other.run.run === each.run)
      if (!lead) {
        throw new Error(`the report has no barangay file for ${storm.name}, ${each.run}`)
      }
      const barangay = barangayIn(lead, psgc)
      const units = unitsIn(barangay, planFlood(storm, each), each)
      return {
        cells: [
          issuedWords(each),
          `${Math.round(each.rain_mm)} mm over ${formatWeek(each.window.start, each.window.end)}`,
          positionWords(each),
          `${formatCount(barangay.exposed)} (${formatShare(barangay.share)})${barangay.flagged ? ', flagged' : ''}`,
          formatCount(units.doxy100),
          formatCount(units.courses),
          formatCount(units.amox500),
        ],
        strong: each.run === run.run,
      }
    })
  const flood = planFlood(storm, run)
  const forecast = run.lead_days !== null
  return {
    title: forecast ? 'The forecasts made before the rain' : 'The rain that fell (no forecast is archived for this date)',
    table: {
      heads: [
        forecast ? 'Forecast made' : 'Rain',
        'Rain over 3 days',
        'How rare a storm',
        'Residents exposed',
        'Capsules',
        'Courses',
        'Tablets',
      ],
      rows,
    },
    note:
      `In bold: the ${forecast ? 'forecast' : 'rain'} this report is for, as on the map. Units for a ${floodName(flood)}` +
      `${flood.w !== null ? ` with w = ${flood.w}` : ''}. Rain over the river basins that drain into Quezon City.`,
  }
}

/**
 * Where the stock goes: the health centers that hold the barangay's stock (C7, centers.json's
 * barangay_centers), each with the share it holds and its whole need for the forecast, the
 * other barangays each one holds stock for, and any center in the barangay C7 leaves out.
 */
function centerSection(input: ReportInput, name: string): ReportContent['centers'] {
  const { centers, storm, run, psgc, shapes } = input
  const held = centers.barangay_centers[psgc]
  const needs = centers.needs[storm.storm]?.[run.run]?.[PLAN_FLOOD]
  if (!held?.length || !needs) {
    throw new Error(`centers.json has no health centers or no need for ${psgc}, ${storm.storm}, ${run.run}: rerun python -m src.app_data`)
  }
  const listed = new Map(centers.centers.map((center) => [center.facility_code, center]))
  const names = new Map(shapes.features.map(({ properties }) => [properties.psgc, properties.name]))
  const rows = held.map((each) => {
    const center = listed.get(each.facility_code)
    const need = needs[each.facility_code]
    if (!center || !need || center.lat === null || center.lon === null) {
      throw new Error(`centers.json: health center ${each.facility_code} has no need or no place: rerun python -m src.app_data`)
    }
    return { each, center, need, title: titleCase(center.name) }
  })
  const first = rows[0]
  const intro =
    first.each.rule === 'split'
      ? `${name} has ${rows.length} health centers. Its need is split among them by where its residents live: ` +
        'each center holds the share of residents who live nearer to it than to the others.'
      : first.each.rule === 'nearest'
        ? `${name} has no health center of its own, so all of its need goes to the nearest one, ${first.title} in ` +
          `${first.center.barangay}, ${formatKm(first.each.km ?? 0)} from the middle of ${name}.`
        : `All of ${name}'s need goes to its health center, ${first.title}.`
  // The other barangays each center holds stock for, with the share it holds where it is not all
  const others = rows.map(({ each }) =>
    Object.entries(centers.barangay_centers)
      .filter(([other]) => other !== psgc)
      .flatMap(([other, list]) =>
        list
          .filter((row) => row.facility_code === each.facility_code)
          .map((row) => `${names.get(other) ?? other}${row.share < 1 ? ` (${percent(row.share)})` : ''}`),
      )
      .sort((a, b) => a.localeCompare(b)),
  )
  const serves = rows.flatMap(({ title }, i) =>
    others[i].length ? [`${title} also holds stock for ${listWords(others[i])}.`] : [],
  )
  const alone = rows.filter((_, i) => others[i].length === 0).map(({ title }) => title)
  if (alone.length) {
    serves.push(`${listWords(alone)} ${alone.length > 1 ? 'hold' : 'holds'} stock for ${name} only.`)
  }
  const leftOut = centers.centers
    .filter((center) => center.psgc === psgc && !center.gets_stock)
    .map(
      (center) =>
        `The registry also lists ${titleCase(center.name)} in ${name}. It gets no stock: ` +
        `${center.left_out ? (LEFT_OUT_WORDS[center.left_out] ?? center.left_out) : 'C7 leaves it out'}.`,
    )
  const flood = planFlood(storm, run)
  return {
    intro,
    table: {
      heads: ['', 'Health center', 'In barangay', `Share of ${name}'s need`, 'Capsules', 'Courses', 'Tablets'],
      rows: rows.map(({ each, center, need, title }, i) => ({
        cells: [
          String(i + 1),
          title,
          center.barangay,
          percent(each.share),
          formatCount(need.doxy100),
          formatCount(need.courses),
          formatCount(need.amox500),
        ],
      })),
    },
    serves,
    leftOut,
    note:
      "Capsules, courses and tablets: the center's whole need, for every barangay it holds stock for, in a " +
      `${floodName(flood)}, rounded up to whole units, the level stock is ordered at.`,
    pins: rows.map(({ center }, i) => ({ number: i + 1, at: [center.lon!, center.lat!] })),
  }
}

/** Quezon City's case forecast for the week after the map's date, as the city panel gives it, said to be the whole city's. */
function citySection({ forecast, week, date }: ReportInput): ReportContent['city'] {
  const title = "Quezon City's case forecast (the whole city)"
  const whole = 'LEPTON forecasts cases for the whole city; it does not forecast cases for each barangay.'
  const model = week?.forecasts[forecast.map_model]
  if (!week || !model) {
    return { title, lines: ['No city forecast for the week after this date.', whole], badge: null }
  }
  const level = levelOf(model.p_breach, forecast.levels)
  const made = weekStart(date)
  return {
    title,
    lines: [
      `${Math.round(model.mu)} cases expected in the week of ${formatWeek(week.start, week.end)} ` +
        `(${rangePercent(forecast)} range ${model.low}–${model.high}).`,
      `Chance of an outbreak: ${formatChance(model.p_breach)} that the week ends above the epidemic threshold ` +
        `(${thresholdCount(week.threshold)} cases). Level: ${LEVEL_NAMES[level]}.`,
      `Made in the week of ${formatWeek(made, addDays(made, 6))}, the week of the map's date, by ` +
        `${forecast.map_model}, LEPTON's forecast model.`,
      whole,
    ],
    badge: isSimulated(forecast, week) ? simulatedLabel(forecast) : null,
  }
}

/** How the figures were made, in plain words, one step a line (the paper's methodology, shortened). */
function methodLines(storms: StormsFile, run: StormRun, flood: Flood): string[] {
  const levels = run.levels_mm
  const rain = run.issued
    ? `The ${run.rain_product} forecast (via Open-Meteo), made ${fullDate(run.issued)}, of the rain`
    : `The rain that fell, as ${run.rain_product} measured it,`
  const days = storms.counting.high_risk_days
  return [
    `Rain. ${rain} over the river basins that drain into Quezon City (the Marikina, San Juan and ` +
      `Tullahan rivers), added up over 3 days. It is set against ${run.levels_product}'s rain over the same basins in ` +
      `the ${run.levels_years} years before ${run.window.start.slice(0, 4)}: on that scale a 5-year storm brings ${levels['R(5)']} mm ` +
      `in 3 days, a 25-year storm ${levels['R(25)']} mm and a 100-year storm ${levels['R(100)']} mm. Below ` +
      `${levels.R0} mm (half the 5-year rain) nobody counts as exposed.`,
    "Flood zones. Project NOAH's maps of the areas a 5-, 25- and 100-year rain floods. A storm between two of these " +
      'rains falls between the two maps. Residents count as exposed when they live in a zone the rain floods, at any ' +
      'depth.',
    "Residents. WorldPop's 2024 population map, fitted to each barangay's 2024 census total. Children under 18 come " +
      "from the 2020 census's ages; pregnant women from 2024's registered births × 0.75, shared out by each " +
      "barangay's women aged 15 to 49.",
    `Risk (DOH DM 2023-0309). A flood of ${days} days or more makes every exposed adult high risk. In a shorter flood, ` +
      'adults with a wound, or with floodwater in the eyes, nose or mouth, are at moderate risk' +
      `${flood.w !== null ? ` (their share, w, is not known and is set at ${flood.w})` : ''}; the rest are at low risk.`,
    "Health centers. A barangay's need goes to its health center. A barangay with several splits it by where its " +
      'residents live, each center taking those who live nearest it; one with none sends it to the nearest center, ' +
      'measured from its middle. Health centers and barangay health stations come from the DOH National Health ' +
      'Facility Registry; the City Health Office is not a distribution point.',
    `Flagged. A barangay is flagged when ${percent(storms.flag_share)} or more of its residents live in zones the rain floods.`,
  ]
}

/**
 * Everything the report says about one barangay, for the forecast and date the map shows.
 * Stops with an error if a file lacks what it needs.
 */
export function reportContent(input: ReportInput): ReportContent {
  const { storms, storm, run, leads, psgc, link, made } = input
  const lead = leads.find((each) => each.run.run === run.run)
  if (!lead) {
    throw new Error(`the report has no barangay file for ${storm.name}, ${run.run}`)
  }
  const barangay = barangayIn(lead, psgc)
  const { name } = barangay
  const flood = planFlood(storm, run) // the flood the map shows: D = 1, w = 0.5
  const units = unitsIn(barangay, flood, run)
  return {
    fileName: reportFileName(name, storm, run),
    docTitle: `LEPTON barangay stock report: ${name}, ${storm.name} (${run.issued ? 'forecast made ' : ''}${issuedWords(run)})`,
    label: storms.label,
    name,
    about: `Quezon City · PSGC ${psgc} · ${formatCount(barangay.pop_2024)} residents (2024 census)`,
    flag: flagText(barangay, storms, run),
    storm: storm.name,
    forecastLine:
      `${run.issued ? `Forecast made ${issuedWords(run)}` : `The rain that fell (${run.rain_product})`}: ` +
      `${Math.round(run.rain_mm)} mm of rain over ${formatWeek(run.window.start, run.window.end)} on the river ` +
      `basins that drain into Quezon City, ${positionWords(run)}.`,
    cityLine: cityLine(input, lead, barangay),
    figures: figures(barangay, units),
    figuresNote:
      (barangay.exposed === 0
        ? `Nobody in ${name} lives in a zone ${rainName(run)} floods, so it needs no stock for ${runName(run)}. `
        : '') +
      `For a ${floodName(flood)}${flood.w !== null ? ` with w = ${flood.w}` : ''}, as on the map ` +
      '(w: the share of exposed adults with a wound, or with floodwater in the eyes, nose or mouth).',
    stock: stockSection(storms, run, barangay),
    leads: leadSection(input),
    centers: centerSection(input, name),
    map: {
      psgc,
      classes: new Map([...lead.barangays].map(([each, row]) => [each, row.class])),
      legend: storms.classes.map((share) => ({ cls: share.class, label: classLabel(share, storms.classes) })),
      caption:
        `Shades: the share of each barangay's residents in zones ${rainName(run)} floods. Outlined in black: ` +
        `${name}. Numbered: the health centers that hold its stock, as in the table. Boundaries: PSA and NAMRIA ` +
        'via OCHA (CC BY-IGO).',
    },
    city: citySection(input),
    method: methodLines(storms, run, flood),
    limits: LIMITS,
    sources: SOURCES,
    made:
      `Made ${madeWords(made)} by LEPTON, from its published data files: storms.json, ${run.file}, centers.json and ` +
      'city_forecast.json.',
    link,
  }
}
