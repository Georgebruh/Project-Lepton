import { Link, useLocation } from 'react-router'
import Button from '../components/Button.tsx'
import Icon from '../components/Icon.tsx'
import { formatCount } from './forecast.ts'
import PanelModes from './PanelModes.tsx'
import {
  centerName,
  centerNeeds,
  forecastRuns,
  issuedLine,
  leadLabel,
  leadWords,
  planFlood,
  rainLine,
  stockList,
  stockListName,
  stormDate,
  stormsWithForecasts,
} from './plan.ts'
import type { CentersFile, Storm, StormRun, StormsFile } from './planData.ts'
import { MAP_PATHS, PLAN_PARAMS } from './routes.ts'
import './PlanPanel.css'

/** How many health centers the panel lists; the stock list has them all. */
const TOP_CENTERS = 4

/** The byte-order mark, U+FEFF: at the start of a file it tells a spreadsheet the file is UTF-8. */
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff)

type PlanPanelProps = {
  /** The city's name, as the heading writes it. */
  city: string
  storms: StormsFile
  centers: CentersFile
  /** The storm shown, or undefined: then the panel lists the storms to choose from. */
  storm: Storm | undefined
  /** Its forecast the reader picked: 1 day ahead unless the address says otherwise. */
  run: StormRun | undefined
  /** The chosen date, YYYY-MM-DD: a storm opened from the list goes back to it. */
  date: string
  /** Whether the chosen date has a storm forecast (when the reader asked for the list, it may). */
  stormOnDate: boolean
  /** How many barangays the map has (142), for "72 of 142". */
  barangays: number
  /** Called with the lead time, in days, of the forecast the reader picks. */
  onLead: (days: number) => void
}

/** The city panel's prophylaxis plan. */
export default function PlanPanel(props: PlanPanelProps) {
  const { city, storms, centers, storm, run, date, stormOnDate, barangays, onLead } = props
  const { search } = useLocation()
  return (
    <div className="plan-panel">
      <PanelModes mode="prophylaxis" />
      <div className="plan-panel-heading">
        <div className="plan-panel-title">
          {/* Takes the keyboard when the plan opens (MapLayout) */}
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
      ) : (
        <StormList storms={storms.storms} date={date} stormOnDate={stormOnDate} />
      )}
      {/* Read out when the reader picks another forecast or date. */}
      <p className="visually-hidden" aria-live="polite">
        {storm && run
          ? planWords(storm, run, barangays)
          : `${stormOnDate ? '' : 'No storm forecast for this date. '}Choose a storm with archived forecasts.`}
      </p>
    </div>
  )
}

/** A forecast's totals in one sentence. */
function planWords(storm: Storm, run: StormRun, barangays: number): string {
  const flood = planFlood(storm, run)
  return (
    `${storm.name}, forecast ${leadWords(run.lead_days ?? 1)}: ${run.flagged} of ${barangays} barangays flagged, ` +
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

/** The panel's numbers for one forecast: its rain, the totals, the top health centers and the export. */
function PlanNumbers({ storms, centers, storm, run, barangays, onLead }: PlanNumbersProps) {
  const flood = planFlood(storm, run)
  const needs = centerNeeds(centers, storm.storm, run.run, flood.key)
  const top = needs.slice(0, TOP_CENTERS)
  const anyNeed = needs.some(({ units }) => units.doxy100 + units.courses + units.amox500 > 0)
  return (
    <>
      <section className="plan-panel-rain" aria-label="Rain forecast">
        <div className="plan-panel-rain-head">
          <p id="plan-panel-made" className="label-ui-s">
            Forecast made
          </p>
          <div className="plan-panel-leads" role="group" aria-labelledby="plan-panel-made">
            {forecastRuns(storm).map((each) => {
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
        </div>
        <p className="plan-panel-rain-line label-ui">{rainLine(run)}</p>
        <p className="plan-panel-muted body-s">{issuedLine(run)}</p>
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

/** One of the panel's totals: the number in Data/L over what it counts. */
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
  /** Whether the chosen date has a storm forecast: the list is then shown because the reader asked. */
  stormOnDate: boolean
}

/** The storms with archived forecasts to choose from. */
function StormList({ storms, date, stormOnDate }: StormListProps) {
  const { search } = useLocation()
  return (
    <section className="plan-panel-none" aria-label="Storms with archived forecasts">
      {!stormOnDate && <h3 className="body-m">No storm forecast for this date.</h3>}
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

/** The query of a link that opens a storm from the list. */
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

/** Saves text as a file, as a link with `download` does. */
function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([BYTE_ORDER_MARK, text], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
