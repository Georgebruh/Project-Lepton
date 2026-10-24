import { Link, useLocation } from 'react-router'
import Button from '../components/Button.tsx'
import Icon from '../components/Icon.tsx'
import { formatCount } from './forecast.ts'
import PanelModes from './PanelModes.tsx'
import {
  centerName,
  centerNeeds,
  forecastRuns,
  fullDate,
  issuedLine,
  leadLabel,
  leadWords,
  planFlood,
  planRuns,
  rainLine,
  stockList,
  stockListName,
  stormDate,
  stormsWithForecasts,
} from './plan.ts'
import type { CentersFile, Storm, StormRun, StormsFile } from './planData.ts'
import { MAP_PATHS, PLAN_PARAMS } from './routes.ts'
import './PlanPanel.css'

/** How many health centers the panel lists (Figma: "top 4 of 66"); the stock list has them all. */
const TOP_CENTERS = 4

/** The byte-order mark, U+FEFF: at the start of a file it tells a spreadsheet the file is UTF-8. */
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff)

type PlanPanelProps = {
  /** The city's name, as the heading writes it. */
  city: string
  storms: StormsFile
  centers: CentersFile
  /** The storm (or F16, the day's plan) shown, or undefined: then the panel lists the storms to choose from. */
  storm: Storm | undefined
  /** Its forecast the reader picked: 1 day ahead unless the address says otherwise. */
  run: StormRun | undefined
  /** The chosen date, YYYY-MM-DD: a storm opened from the list goes back to it. */
  date: string
  /** Whether the chosen date has a plan, a storm's or (F16) its own (when the reader asked for the list, it may). */
  planOnDate: boolean
  /** F16: whether the chosen date's daily plans are still on their way. */
  loading: boolean
  /** How many barangays the map has (142), for "72 of 142". */
  barangays: number
  /** Called with the lead time, in days, of the forecast the reader picks. */
  onLead: (days: number) => void
}

/**
 * F5: the city panel's prophylaxis plan, Figma frame 3's "Panel" (node 56:459): the forecast's
 * rain, with the lead chips that switch between the forecasts made 1, 2 and 3 days ahead; the
 * barangays flagged, residents exposed and Quezon City's stock; the 4 health centers needing the
 * most doxycycline; and Export stock list, every health center's need as a CSV file. Every number
 * is the chosen forecast's in storms.json and centers.json, for a 1-day flood with w = 0.5
 * (plan.ts, PLAN_FLOOD).
 *
 * A date without a storm forecast lists the storms to choose from. While a storm is shown, "All
 * storms" (beside the heading; not in Figma) goes back to that list.
 *
 * F16: every date has a plan, the storm's on a storm's dates and the day's own on the others, so
 * the list shows only when the reader asks for it, with a link back to the date's plan. A day
 * before ECMWF's archive has no forecast to choose: its plan is the rain that fell. Most days'
 * plans are zero: too little rain to flood, so no stock.
 */
export default function PlanPanel(props: PlanPanelProps) {
  const { city, storms, centers, storm, run, date, planOnDate, loading, barangays, onLead } = props
  const { search } = useLocation()
  return (
    <div className="plan-panel">
      <PanelModes mode="prophylaxis" />
      <div className="plan-panel-heading">
        <div className="plan-panel-title">
          {/* F11: takes the keyboard when the plan opens (MapLayout) */}
          <h2 className="plan-panel-city heading-l" tabIndex={-1}>
            {city}
          </h2>
          {storm && (
            <Link to={MAP_PATHS[3] + listSearch(search)} preventScrollReset className="plan-panel-all label-ui">
              <Icon name="chevron-left" size={16} />
              All storms
            </Link>
          )}
        </div>
        <p className="plan-panel-subtitle label-ui-s">Prophylaxis plan · next 1–3 days · by barangay</p>
      </div>
      {storm && run ? (
        <PlanNumbers
          storms={storms}
          centers={centers}
          storm={storm}
          run={run}
          barangays={barangays}
          onLead={onLead}
        />
      ) : loading ? (
        <p className="plan-panel-muted body-s">Loading the plan for this date…</p>
      ) : (
        <StormList storms={storms.storms} date={date} planOnDate={planOnDate} />
      )}
      {/* Read out when the reader picks another forecast or date (Figma has no text here). F11:
          always in the page, so the storm list is read out too. */}
      <p className="visually-hidden" aria-live="polite">
        {storm && run
          ? planWords(storm, run, barangays)
          : loading
            ? ''
            : `${planOnDate ? '' : 'No plan for this date. '}Choose a storm with archived forecasts.`}
      </p>
    </div>
  )
}

/** A forecast's totals in one sentence, as a screen reader hears them when the forecast or date changes. */
function planWords(storm: Storm, run: StormRun, barangays: number): string {
  const flood = planFlood(storm, run)
  const made = run.lead_days === null ? 'the rain that fell' : `forecast ${leadWords(run.lead_days)}`
  return (
    `${storm.name}, ${made}: ${run.flagged} of ${barangays} barangays flagged, ` +
    `${formatCount(flood.exposed)} residents exposed, ${formatCount(flood.doxy100)} doxycycline capsules, ` +
    `${formatCount(flood.courses)} children's courses and ${formatCount(flood.amox500)} amoxicillin tablets. ` +
    'Stock planning, not prescriptions.'
  )
}

type PlanNumbersProps = {
  storms: StormsFile
  centers: CentersFile
  storm: Storm
  run: StormRun
  barangays: number
  onLead: (days: number) => void
}

/**
 * The panel's numbers for one forecast: its rain, the totals, the top health centers and the
 * export. F16: for the rain that fell (a day before ECMWF's archive) the rain card says so, with no
 * lead chips.
 */
function PlanNumbers({ storms, centers, storm, run, barangays, onLead }: PlanNumbersProps) {
  const forecast = run.lead_days !== null
  const flood = planFlood(storm, run)
  const needs = centerNeeds(centers, storm.storm, run.run, flood.key)
  const top = needs.slice(0, TOP_CENTERS)
  const anyNeed = needs.some(({ units }) => units.doxy100 + units.courses + units.amox500 > 0)
  return (
    <>
      <section className="plan-panel-rain" aria-label={forecast ? 'Rain forecast' : 'Rain that fell'}>
        <div className="plan-panel-rain-head">
          <p id="plan-panel-made" className="label-ui-s">
            {forecast ? 'Forecast made' : 'Rain that fell'}
          </p>
          {forecast && (
            <div className="plan-panel-leads" role="group" aria-labelledby="plan-panel-made">
              {planRuns(storm).map((each) => {
                const days = each.lead_days ?? 1
                return (
                  <button
                    key={each.run}
                    type="button"
                    className="plan-panel-lead label-ui-s"
                    aria-pressed={each.run === run.run}
                    aria-label={leadWords(days)}
                    onClick={() => onLead(days)}
                  >
                    {leadLabel(days)}
                  </button>
                )
              })}
            </div>
          )}
        </div>
        <p className="plan-panel-rain-line label-ui">{rainLine(run)}</p>
        <p className="plan-panel-muted body-s">{issuedLine(run)}</p>
        {!forecast && (
          <p className="plan-panel-muted body-s">
            No forecast is archived for this date, so the plan uses the rain {run.rain_product} measured.
          </p>
        )}
      </section>

      <section className="plan-panel-totals" aria-label="Totals">
        <div className="plan-panel-totals-row">
          <Total value={`${run.flagged} of ${barangays}`} label="barangays flagged" />
          <Total value={formatCount(flood.exposed)} label="residents exposed" />
        </div>
        <div className="plan-panel-totals-row">
          <Total value={formatCount(flood.doxy100)} label="doxycycline 100 mg capsules, adults" />
          <Total value={formatCount(flood.courses)} label="children's courses, dosed by weight" />
        </div>
        <p className="plan-panel-muted body-s">
          Plus {formatCount(flood.amox500)} amoxicillin 500 mg tablets for pregnant women.
        </p>
      </section>

      <section className="plan-panel-centers" aria-labelledby="plan-panel-centers-title">
        <h3 id="plan-panel-centers-title" className="plan-panel-centers-title label-ui-s">
          Stock by health center · top {top.length} of {needs.length}
        </h3>
        {anyNeed ? (
          <table className="plan-panel-centers-table">
            <thead>
              <tr>
                <th scope="col" className="body-s">
                  <span className="visually-hidden">Health center</span>
                </th>
                <th scope="col" className="body-s">
                  Doxycycline
                </th>
                <th scope="col" className="body-s">
                  Courses
                </th>
              </tr>
            </thead>
            <tbody>
              {top.map((need) => (
                <tr key={need.facilityCode}>
                  <th scope="row" className="label-ui">
                    {centerName(need.name)}
                  </th>
                  <td className="data-m">{formatCount(need.units.doxy100)}</td>
                  <td className="data-m">{formatCount(need.units.courses)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="plan-panel-muted body-s">No health center needs stock for this forecast.</p>
        )}
      </section>

      <div className="plan-panel-actions">
        <Button
          className="plan-panel-action"
          onClick={() => download(stockListName(storm, run), stockList(storms, centers, storm, run))}
        >
          Export stock list
        </Button>
        <p className="plan-panel-note body-s">
          Stock planning, not prescriptions. DOH DM 2023-0309 requires a doctor's consultation before any prophylaxis.
        </p>
      </div>
    </>
  )
}

type TotalProps = {
  /** The number, already written out: "789,689". */
  value: string
  /** What it counts: "residents exposed". */
  label: string
}

/** One of the panel's totals: the number in Data/L over what it counts (Figma "Totals", node 56:693). */
function Total({ value, label }: TotalProps) {
  return (
    <p className="plan-panel-total">
      <span className="data-l">{value}</span>
      <span className="plan-panel-muted body-s">{label}</span>
    </p>
  )
}

type StormListProps = {
  storms: Storm[]
  /** The chosen date: a storm opened from the list goes back to it. */
  date: string
  /** Whether the chosen date has a plan: the list is then shown because the reader asked. */
  planOnDate: boolean
}

/**
 * The storms with archived forecasts to choose from (the app plan, F5): on a date without a
 * plan, which the panel says, or after "All storms". Each opens at the date its 1-day-ahead
 * forecast's rain starts. Figma has no frame for it; it uses the panel's own styles. F16: when the
 * date has a plan, a link above the storms goes back to it.
 */
function StormList({ storms, date, planOnDate }: StormListProps) {
  const { search } = useLocation()
  return (
    <section className="plan-panel-none" aria-label="Storms with archived forecasts">
      {planOnDate ? (
        <Link to={MAP_PATHS[3] + planSearch(search)} preventScrollReset className="plan-panel-storm label-ui">
          Back to the plan for {fullDate(date)}
        </Link>
      ) : (
        <h3 className="body-m">No plan for this date.</h3>
      )}
      <p className="plan-panel-muted body-s">Choose a storm with archived forecasts:</p>
      <ul className="plan-panel-storms">
        {stormsWithForecasts(storms).map((storm) => (
          <li key={storm.storm}>
            <Link
              to={MAP_PATHS[3] + stormSearch(search, storm, date)}
              preventScrollReset
              className="plan-panel-storm label-ui"
            >
              {storm.name}
            </Link>
            <span className="plan-panel-muted body-s">
              {rainLine(forecastRuns(storm)[0])}, forecast {leadWords(1)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

/**
 * The query of a link that opens a storm from the list: the storm's date, its forecast 1 day
 * ahead, and the date to go back to when the reader leaves the plan (?from=, routes.ts): the
 * chosen date now, unless an earlier storm from the list already set it.
 */
function stormSearch(search: string, storm: Storm, date: string): string {
  const params = new URLSearchParams(search)
  if (!params.has(PLAN_PARAMS.from)) {
    params.set(PLAN_PARAMS.from, date)
  }
  params.set('date', stormDate(storm))
  params.delete(PLAN_PARAMS.list)
  params.delete(PLAN_PARAMS.lead)
  return `?${params}`
}

/** The query of "All storms": the list, at the same date (?storms=all). */
function listSearch(search: string): string {
  const params = new URLSearchParams(search)
  params.set(PLAN_PARAMS.list, 'all')
  params.delete(PLAN_PARAMS.lead)
  return `?${params}`
}

/** F16: the query of the link from the list back to the date's plan: the same date, without ?storms=all. */
function planSearch(search: string): string {
  const params = new URLSearchParams(search)
  params.delete(PLAN_PARAMS.list)
  return `?${params}`
}

/**
 * Saves text as a file, as a link with `download` does. The file starts with a byte-order mark,
 * so a spreadsheet reads it as UTF-8 (the ñ in Doña Imelda).
 */
function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([BYTE_ORDER_MARK, text], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
