import { useState, type ReactNode } from 'react'
import Button from '../components/Button.tsx'
import Tab from '../components/Tab.tsx'
import Facts from './Facts.tsx'
import { formatCount, formatWeek } from './forecast.ts'
import {
  centerName,
  centerNeeds,
  formatShare,
  leadLabel,
  leadWords,
  planFlood,
  planRuns,
  stockList,
  stockListName,
} from './plan.ts'
import type { CentersFile, Storm, StormRun, StormsFile } from './planData.ts'
import WordHelp, { type Word } from './WordHelp.tsx'
import './PlanPanel.css'

/** The byte-order mark, U+FEFF: at the start of a file it tells a spreadsheet the file is UTF-8. */
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff)

/** The plan's three views, one at a time under the forecast's rain. */
type PlanView = 'summary' | 'barangays' | 'centers'
const VIEWS: { view: PlanView; name: string }[] = [
  { view: 'summary', name: 'Summary' },
  { view: 'barangays', name: 'Barangays' },
  { view: 'centers', name: 'Health centers' },
]

type PlanPanelProps = {
  /** The city's name, as the heading writes it. */
  city: string
  storms: StormsFile
  centers: CentersFile
  /** The plan shown, a storm's or the date's own; undefined when the date has none. */
  storm: Storm | undefined
  /** Its forecast the reader picked: 1 day ahead unless the address says otherwise. */
  run: StormRun | undefined
  /** Whether the chosen date's daily plans are still on their way. */
  loading: boolean
  /** How many barangays the map has (142), for "72 of 142". */
  barangays: number
  /** The Barangays view: the list of barangays (MapProphylaxis's MapList). */
  list: ReactNode
  /** Called with the lead time, in days, of the forecast the reader picks. */
  onLead: (days: number) => void
}

/** The city panel's prophylaxis plan. */
export default function PlanPanel(props: PlanPanelProps) {
  const { city, storms, centers, storm, run, loading, barangays, list, onLead } = props
  return (
    <div className="plan-panel">
      {/* Takes the keyboard when the plan opens (MapLayout) */}
      <h2 className="plan-panel-city heading-l" tabIndex={-1}>
        {city}
      </h2>
      {storm && run ? (
        <PlanNumbers
          centers={centers}
          storm={storm}
          run={run}
          barangays={barangays}
          list={list}
          onLead={onLead}
        />
      ) : (
        <p className="plan-panel-none body-m">{loading ? 'Loading the plan for this date…' : 'No plan for this date.'}</p>
      )}
      <div className="plan-panel-foot">
        {storm && run && (
          <Button
            className="plan-panel-action"
            onClick={() => download(stockListName(storm, run), stockList(storms, centers, storm, run))}
          >
            Export stock list
          </Button>
        )}
        <div className="plan-panel-note-row">
          <p className="plan-panel-note body-s">Stock planning, not prescriptions.</p>
          <WordHelp words={helpWords(storms, storm)} />
        </div>
      </div>
      {/* Read out when the reader picks another forecast or date. */}
      <p className="visually-hidden" aria-live="polite">
        {storm && run ? planWords(storm, run, barangays) : loading ? '' : 'No plan for this date.'}
      </p>
    </div>
  )
}

/** A forecast's totals in one sentence. */
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

/** The rain a run puts in the plan: "224 mm over 22–24 Jul 2024". */
function rainAmount(run: StormRun): string {
  return `${Math.round(run.rain_mm)} mm over ${formatWeek(run.window.start, run.window.end)}`
}

type PlanNumbersProps = {
  centers: CentersFile
  storm: Storm
  run: StormRun
  barangays: number
  list: ReactNode
  onLead: (days: number) => void
}

/** The panel's numbers for one forecast: which forecast and its rain, then one of the three views. */
function PlanNumbers({ centers, storm, run, barangays, list, onLead }: PlanNumbersProps) {
  const [view, setView] = useState<PlanView>('summary')
  const forecast = run.lead_days !== null
  const flood = planFlood(storm, run)
  return (
    <>
      <Facts
        facts={
          forecast
            ? [
                { label: 'Forecast made', value: <LeadSwitch storm={storm} run={run} onLead={onLead} /> },
                { label: 'Rain', value: rainAmount(run) },
              ]
            : [
                // No forecast is archived for this date: the plan uses the rain that was measured
                { label: 'Forecast made', value: 'None archived' },
                { label: `Rain ${run.rain_product} measured`, value: rainAmount(run) },
              ]
        }
      />
      <div className="plan-panel-views" role="group" aria-label="View">
        {VIEWS.map((each) => (
          <Tab key={each.view} selected={view === each.view} onClick={() => setView(each.view)}>
            {each.name}
          </Tab>
        ))}
      </div>
      <div className="plan-panel-view">
        {view === 'summary' && (
          <>
            <div className="plan-panel-headline">
              <Total value={`${run.flagged} of ${barangays}`} label="barangays flagged" />
              <Total value={formatCount(flood.exposed)} label="residents exposed" />
            </div>
            <section className="plan-panel-stock" aria-labelledby="plan-panel-stock-title">
              <h3 id="plan-panel-stock-title" className="plan-panel-stock-title label-ui-s">
                Stock needed
              </h3>
              <Facts
                facts={[
                  { label: 'Doxycycline 100 mg capsules, adults', value: formatCount(flood.doxy100) },
                  { label: "Children's courses", value: formatCount(flood.courses) },
                  { label: 'Amoxicillin 500 mg tablets, pregnant women', value: formatCount(flood.amox500) },
                ]}
              />
            </section>
          </>
        )}
        {view === 'barangays' && list}
        {view === 'centers' && <CenterTable centers={centers} storm={storm} run={run} />}
      </div>
    </>
  )
}

type LeadSwitchProps = {
  storm: Storm
  run: StormRun
  onLead: (days: number) => void
}

/** The forecasts to choose from, by how many days before the rain each was made. */
function LeadSwitch({ storm, run, onLead }: LeadSwitchProps) {
  return (
    <span className="plan-panel-leads" role="group" aria-label="Forecast made">
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
    </span>
  )
}

type CenterTableProps = {
  centers: CentersFile
  storm: Storm
  run: StormRun
}

/** Every health center's stock for the forecast, the most first. */
function CenterTable({ centers, storm, run }: CenterTableProps) {
  const needs = centerNeeds(centers, storm.storm, run.run, planFlood(storm, run).key)
  if (!needs.some(({ units }) => units.doxy100 + units.courses + units.amox500 > 0)) {
    return <p className="plan-panel-muted body-s">No health center needs stock for this forecast.</p>
  }
  return (
    <table className="plan-panel-centers-table">
      <thead>
        <tr>
          <th scope="col" className="label-ui-s">
            Health center
          </th>
          <th scope="col" className="label-ui-s">
            Doxycycline
          </th>
          <th scope="col" className="label-ui-s">
            Courses
          </th>
        </tr>
      </thead>
      <tbody>
        {needs.map((need) => (
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
  )
}

type TotalProps = {
  /** The number, already written out: "789,689". */
  value: string
  /** What it counts: "residents exposed". */
  label: string
}

/** One of the plan's headline numbers: the number in Data/L over what it counts. */
function Total({ value, label }: TotalProps) {
  return (
    <p className="plan-panel-total">
      <span className="data-l">{value}</span>
      <span className="plan-panel-muted body-s">{label}</span>
    </p>
  )
}

/** What the plan's words mean, for the panel's ? (WordHelp). */
function helpWords(storms: StormsFile, storm: Storm | undefined): Word[] {
  const leads = storm ? planRuns(storm).flatMap((run) => (run.lead_days === null ? [] : [run.lead_days])) : []
  const days = leads.length > 1 ? `${leads.slice(0, -1).join(', ')} or ${leads[leads.length - 1]}` : '1, 2 or 3'
  return [
    {
      term: `Forecast made ${days} days ahead`,
      meaning:
        'How many days before the rain its forecast was made. An earlier forecast gives more time to move ' +
        'stock, but is less sure.',
    },
    { term: 'Residents exposed', meaning: 'People who live where the forecast rain is expected to flood.' },
    { term: 'Flagged', meaning: `A barangay where ${formatShare(storms.flag_share)} or more of residents are exposed.` },
    {
      term: 'Doxycycline 100 mg capsules',
      meaning: 'The antibiotic adults take to lower their chance of leptospirosis after wading in floodwater.',
    },
    { term: "Children's courses", meaning: 'Doses for children, measured by their weight.' },
    { term: 'Amoxicillin 500 mg tablets', meaning: 'For pregnant women, who should not take doxycycline.' },
    {
      term: 'Stock planning, not prescriptions',
      meaning: 'How much to keep in stock. A doctor decides who takes it (DOH DM 2023-0309).',
    },
  ]
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
