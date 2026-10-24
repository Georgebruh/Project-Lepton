import { formatKm, type LonLat } from '../exposed/nearest.ts'
import { formatCount } from '../map/forecast.ts'
import {
  PLAN_FLOOD,
  classLabel,
  formatShare,
  fullDate,
  leadWords,
  planFlood,
  positionWords,
  rainLine,
  titleCase,
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

/* What the barangay report says, for the health centers and barangay health stations that hold its stock. */

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
  /** The map's address, which opens this forecast again (the cover's QR code). */
  link: string
  /** When the report is made. */
  made: Date
}

/** A table: its column heads and its rows of cells; a `strong` row is set in bold. */
export type Table = { heads: string[]; rows: { cells: string[]; strong?: boolean }[] }

/** One unit to stock: its count in the map's flood, what it is, and who it is for. */
export type StockItem = { value: string; unit: string; who: string }

export type ReportContent = {
  fileName: string
  /** The PDF's title, as a PDF reader shows it. */
  docTitle: string
  /** storms.json's label: stock-planning figures, not prescriptions. */
  label: string
  name: string
  /** Under the name on the cover: the city and the barangay's 2024 residents. */
  place: string
  /** When the report was made. */
  made: string
  /** The storm, when the forecast was made, and its rain, for the cover. */
  storm: string
  forecastLine: string
  rainLine: string
  /** Whether the barangay is flagged: the chip's words, the residents exposed, and what flagged means. */
  flag: { flagged: boolean; label: string; headline: string; text: string }
  /** The stock to prepare: a card per unit, and the line under the cards. */
  stock: { items: StockItem[]; note: string }
  centers: {
    /** Each center that holds the stock, as the cover lists them. */
    names: string[]
    /** How the need reaches the centers; null when it all goes to the barangay's own center. */
    intro: string | null
    table: Table
    notes: string[]
    /** Each center's pin on the map: its number in the table and its place. */
    pins: { number: number; at: LonLat }[]
  }
  map: {
    psgc: string
    /** Each barangay's class (0 to 4) in this forecast, by PSGC. */
    classes: Map<string, number>
    legend: { cls: number; label: string }[]
  }
  /** How many units each person gets, a column per flood. */
  counting: { table: Table; notes: string[] }
  /** About these numbers: where they come from and what they cannot claim, one point a line. */
  about: string[]
  sources: string
  link: string
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Why a health center is left out (centers.json's left_out), in the report's words. */
const LEFT_OUT_WORDS: Record<string, string> = {
  'no coordinates': 'the registry gives it no location',
  'point outside its barangay': 'its registered location lies outside its barangay',
}

/** The sources of the figures, with their licences, as one paragraph. */
const SOURCES =
  'Flood hazard maps: Project NOAH, UP Resilience Institute (ODbL). Population: WorldPop 2024 (CC BY 4.0); PSA 2024 ' +
  'census; PSA 2020 census ages via OCHA (CC BY); PSA 2024 registered births (CC BY). Boundaries: PSA and NAMRIA via ' +
  'OCHA (CC BY-IGO). Health centers: DOH National Health Facility Registry. Rain: ECMWF IFS forecasts and ERA5 via ' +
  'Open-Meteo (CC BY 4.0; ERA5 contains modified Copernicus Climate Change Service information); GPM IMERG Late v07 ' +
  '(NASA GES DISC). River basins: HydroBASINS (Lehner and Grill, 2013). Regimens: DOH Department Memorandum 2023-0309.'

/** A share as a whole percentage: 0.5 is "50%". */
function percent(share: number): string {
  return `${Math.round(share * 100)}%`
}

/** Names as a sentence lists them: "A", "A and B", "A, B and C". */
function listWords(names: string[]): string {
  return names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** "1 day", "7 days". */
function days(n: number): string {
  return n === 1 ? '1 day' : `${n} days`
}

/** A name in a file name. */
function slug(name: string): string {
  return name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

/** When the report was made, in the reader's own time: "23 Oct 2026, 22:45". */
function madeWords(when: Date): string {
  const two = (n: number) => String(n).padStart(2, '0')
  return `${when.getDate()} ${MONTHS[when.getMonth()]} ${when.getFullYear()}, ${two(when.getHours())}:${two(when.getMinutes())}`
}

/** A flood of a run in words: "1-day flood". */
function floodName(flood: Flood): string {
  return `${flood.D}-day flood`
}

/** Weeks of flooding: whole weeks, rounded up. */
function floodWeeks(flood: Flood, counting: CountingRules): number {
  return Math.ceil(flood.D / counting.week_days)
}

/** The report's file name, as the stock list names its CSV. */
export function reportFileName(name: string, storm: Storm, run: StormRun): string {
  return `lepton-barangay-report_${slug(name)}_${storm.storm}_${run.run.replace(/\s+/g, '')}.pdf`
}

/** When a forecast was made: "21 Oct 2024, 1 day ahead"; for observed rain, its product. */
function issuedWords(run: StormRun): string {
  return run.issued && run.lead_days !== null
    ? `${fullDate(run.issued)}, ${leadWords(run.lead_days)}`
    : `the rain that fell (${run.rain_product})`
}

/** What the report calls a run's rain: "this forecast's rain", or "this rain". */
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

/** The status band: flagged or not, the residents exposed, and what flagged means. */
function flagSection(storms: StormsFile, run: StormRun, barangay: BarangayRun): ReportContent['flag'] {
  const label = barangay.flagged ? 'Flagged' : 'Not flagged'
  if (barangay.exposed === 0) {
    return {
      flagged: false,
      label,
      headline: 'No resident exposed',
      text: `Nobody in ${barangay.name} lives in a zone ${rainName(run)} floods, so it needs no stock.`,
    }
  }
  return {
    flagged: barangay.flagged,
    label,
    headline:
      `${formatCount(barangay.exposed)} residents exposed ` +
      `(${formatShare(barangay.share)} of ${formatCount(barangay.pop_2024)})`,
    text:
      `They live in zones ${rainName(run)} floods. A barangay is flagged when ${percent(storms.flag_share)} or more ` +
      'of its residents are exposed.',
  }
}

/** The three units: their key, what they are, and who they are for. */
const STOCK: { key: keyof Units; unit: string; who: string }[] = [
  { key: 'doxy100', unit: 'doxycycline 100 mg capsules', who: 'Adults, not pregnant' },
  { key: 'courses', unit: "children's courses", who: 'Children under 18' },
  { key: 'amox500', unit: 'amoxicillin 500 mg tablets', who: 'Pregnant women' },
]

/** The stock to prepare: a card per unit for the map's flood, and whether those counts cover a longer flood. */
function stockSection(storms: StormsFile, run: StormRun, barangay: BarangayRun, flood: Flood): ReportContent['stock'] {
  const units = unitsIn(barangay, flood, run)
  const items: StockItem[] = STOCK.map(({ key, unit, who }) => ({ value: formatCount(units[key]), unit, who }))
  // Each longer flood: covered by these counts, or the units it needs more of
  const longer = run.floods
    .filter((each) => each.key !== flood.key)
    .map((each) => {
      const other = unitsIn(barangay, each, run)
      const more = STOCK.filter(({ key }) => other[key] > units[key])
      if (more.length) {
        return `A ${floodName(each)} needs more: ${listWords(more.map(({ key, unit }) => `${formatCount(other[key])} ${unit}`))}.`
      }
      const fewer =
        each.w === null && other.doxy100 < units.doxy100
          ? `, which needs fewer capsules, as every exposed adult then takes a weekly dose of ${storms.counting.doxy100_high_per_week}`
          : ''
      return `These counts also cover a ${floodName(each)}${fewer}.`
    })
  const unknown = longer.length
    ? ` ${run.lead_days === null ? 'The rain alone' : 'A forecast'} cannot tell how long the flood will last. ${longer.join(' ')}`
    : ''
  return {
    items,
    note:
      `For a ${floodName(flood)}, as on the map.${unknown} Every exposed resident is counted (full coverage). ` +
      'Who gets what: see Details.',
  }
}

/** How many units each person gets, a column per flood of the run. */
function countingSection(storms: StormsFile, run: StormRun): ReportContent['counting'] {
  const { counting } = storms
  const adults = (flood: Flood) =>
    flood.w !== null
      ? `Moderate risk: ${counting.doxy100_moderate} each. Low risk: ${counting.doxy100_low} each.`
      : `High risk: ${counting.doxy100_high_per_week} a week of flooding, so ` +
        `${counting.doxy100_high_per_week * floodWeeks(flood, counting)} each.`
  const courses = (flood: Flood) => {
    const each = Math.max(1, floodWeeks(flood, counting))
    return flood.D < counting.week_days ? '1 course each' : `One a week of flooding, so ${each} each`
  }
  const rows = [
    { cells: ['Doxycycline 100 mg capsules', 'Exposed adults, not pregnant', ...run.floods.map(adults)] },
    { cells: ["Children's courses", 'Exposed children under 18', ...run.floods.map(courses)] },
    {
      cells: [
        'Amoxicillin 500 mg tablets',
        'Exposed pregnant women',
        ...run.floods.map(() => `${counting.amox500_pregnant} each`),
      ],
    },
  ]
  const notes: string[] = []
  const w = run.floods.find((flood) => flood.w !== null)?.w
  if (w !== null && w !== undefined) {
    notes.push(
      'Moderate risk: a wound, or floodwater in the eyes, nose or mouth; the rest are low risk. Nobody knows how many ' +
        `adults that is, so ${percent(w)} are counted as moderate risk. A flood of ${days(counting.high_risk_days)} or ` +
        'more makes every exposed adult high risk.',
    )
  }
  notes.push(
    "A child's course is doxycycline 4 mg/kg once (at most 200 mg) or an alternative; the pharmacy turns courses into " +
      'tablets by weight. A pregnant woman allergic to amoxicillin takes as many erythromycin 250 mg tablets instead. ' +
      'Regimens: DOH DM 2023-0309. Rounded to whole units.',
  )
  return { table: { heads: ['Stock', 'For', ...run.floods.map(floodName)], rows }, notes }
}

/** Where the stock goes. */
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
    const title = titleCase(center.name)
    return { each, center, need, title, named: center.barangay === name ? title : `${title} (in ${center.barangay})` }
  })
  const first = rows[0]
  const intro =
    first.each.rule === 'split'
      ? `${name}'s ${rows.length} health centers share its need by where its residents live: each takes those who ` +
        'live nearest it.'
      : first.each.rule === 'nearest'
        ? `${name} has no health center of its own, so its stock goes to the nearest one, ` +
          `${formatKm(first.each.km ?? 0)} from its middle.`
        : null
  // The other barangays each center holds stock for, with the share it holds where it is not all
  const serves = rows.flatMap(({ each, title }) => {
    const others = Object.entries(centers.barangay_centers)
      .filter(([other]) => other !== psgc)
      .flatMap(([other, list]) =>
        list
          .filter((row) => row.facility_code === each.facility_code)
          .map((row) => `${names.get(other) ?? other}${row.share < 1 ? ` (${percent(row.share)})` : ''}`),
      )
      .sort((a, b) => a.localeCompare(b))
    return others.length ? [`${title} also supplies ${listWords(others)}.`] : []
  })
  const leftOut = centers.centers
    .filter((center) => center.psgc === psgc && !center.gets_stock)
    .map(
      (center) =>
        `${titleCase(center.name)}, also in the registry, gets no stock: ` +
        `${center.left_out ? (LEFT_OUT_WORDS[center.left_out] ?? center.left_out) : 'C7 leaves it out'}.`,
    )
  const split = rows.length > 1
  return {
    names: rows.map(({ named }) => named),
    intro,
    table: {
      heads: ['', 'Health center', ...(split ? [`Share of ${name}`] : []), 'Capsules', 'Courses', 'Tablets'],
      rows: rows.map(({ each, need, named }, i) => ({
        cells: [
          String(i + 1),
          named,
          ...(split ? [percent(each.share)] : []),
          formatCount(need.doxy100),
          formatCount(need.courses),
          formatCount(need.amox500),
        ],
      })),
    },
    notes: [
      `Each center's whole order for a ${floodName(planFlood(storm, run))}, for every barangay it supplies, rounded up.`,
      ...serves,
      ...leftOut,
    ],
    pins: rows.map(({ center }, i) => ({ number: i + 1, at: [center.lon!, center.lat!] })),
  }
}

/** Where the numbers come from and what they cannot claim, in plain words, one point a line. */
function aboutLines(run: StormRun): string[] {
  const mm = (key: string) => `${Math.round(run.levels_mm[key])} mm`
  const rain = run.issued ? "the forecast's rain" : 'the rain that fell'
  return [
    `Rain: ${rain} over 3 days on the river basins that drain into Quezon City. A 5-year storm is rain that heavy ` +
      `about once in 5 years: ${mm('R(5)')} in 3 days here. Below ${mm('R0')} nobody counts as exposed.`,
    "Exposed: living in a zone that Project NOAH's flood maps show flooding at this rain, at any depth. Residents " +
      'from WorldPop 2024, fitted to the 2024 census; children from the 2020 census ages; pregnant women from ' +
      "2024's registered births. Lactating women are not counted apart: DM 2023-0309 gives them no regimen.",
    'Full coverage: every exposed resident is counted, and every course taken. Scale the figures by the share of ' +
      'residents you expect to come forward.',
    "Health centers: a barangay's stock goes to its own health center, is split among several by where its " +
      'residents live, or goes to the nearest one when it has none (DOH National Health Facility Registry). The ' +
      'City Health Office is not a distribution point.',
    'A forecast can miss. For the July 2025 floods, the forecasts made 1 to 3 days ahead put far fewer residents in ' +
      'flooded zones than the rain that fell did. These figures have not been checked against barangay case counts.',
  ]
}

/** Everything the report says about one barangay, for the forecast and date the map shows. */
export function reportContent(input: ReportInput): ReportContent {
  const { storms, storm, run, leads, psgc, link, made } = input
  const lead = leads.find((each) => each.run.run === run.run)
  const barangay = lead?.barangays.get(psgc)
  if (!lead || !barangay) {
    throw new Error(`the report has no barangay ${psgc} for ${storm.name}, ${run.run}: rerun python -m src.app_data`)
  }
  const { name } = barangay
  const flood = planFlood(storm, run) // The flood the map shows: D = 1, w = 0.5
  return {
    fileName: reportFileName(name, storm, run),
    docTitle: `LEPTON barangay stock report: ${name}, ${storm.name} (${run.issued ? 'forecast made ' : ''}${issuedWords(run)})`,
    label: storms.label,
    name,
    place: `Quezon City, ${formatCount(barangay.pop_2024)} residents (2024 census)`,
    made: `Made ${madeWords(made)}`,
    storm: storm.name,
    forecastLine: run.issued ? `Forecast made ${issuedWords(run)}` : `The rain that fell (${run.rain_product})`,
    rainLine: `${rainLine(run)}, ${positionWords(run)}`,
    flag: flagSection(storms, run, barangay),
    stock: stockSection(storms, run, barangay, flood),
    centers: centerSection(input, name),
    map: {
      psgc,
      classes: new Map([...lead.barangays].map(([each, row]) => [each, row.class])),
      legend: storms.classes.map((share) => ({ cls: share.class, label: classLabel(share, storms.classes) })),
    },
    counting: countingSection(storms, run),
    about: aboutLines(run),
    sources: SOURCES,
    link,
  }
}
