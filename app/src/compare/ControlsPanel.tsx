import { useId, useState, type ReactNode } from 'react'
import Badge from '../components/Badge.tsx'
import Icon from '../components/Icon.tsx'
import PanelHeader from '../components/PanelHeader.tsx'
import Tab from '../components/Tab.tsx'
import ToggleRow from '../components/ToggleRow.tsx'
import { SIMULATED_LABEL } from '../map/forecast.ts'
import type { ForecastWeek } from '../map/mapData.ts'
import { RANGE_MODEL, modelStyle } from './models.ts'
import { RECENT_WEEKS, allYearsName, type Period } from './periods.ts'
import { weekTitle, type Layers } from './readout.ts'
import './ControlsPanel.css'

type ControlsPanelProps = {
  /** The models, in the toggles' order (toggleOrder). */
  models: string[]
  /** Which models the chart draws. */
  shown: Record<string, boolean>
  onModel: (model: string, on: boolean) => void
  layers: Layers
  onLayer: (layer: keyof Layers, on: boolean) => void
  period: Period
  /** The year the year tab opens: the one shown, or the last one chosen. */
  year: number
  /** The backtest's years, oldest first. */
  years: number[]
  onPeriod: (period: Period) => void
  /** The range's name, "90%". */
  rangeName: string
  /** The backtest's latest week. */
  latest: ForecastWeek
  simulated: boolean
}

type SectionProps = {
  title: string
  /** The space between the section's rows: Figma's 2 px for toggles, 8 px for the period. */
  tight?: boolean
  children: ReactNode
}

/** One section of the panel under its Panel header, which opens and closes it. */
function Section({ title, tight = false, children }: SectionProps) {
  const [open, setOpen] = useState(true)
  return (
    <div className={tight ? 'controls-panel-section controls-panel-section-tight' : 'controls-panel-section'}>
      <PanelHeader title={title} expanded={open} onToggle={() => setOpen(!open)} />
      {open && (
        <div role="group" aria-label={title} className="controls-panel-rows">
          {children}
        </div>
      )}
    </div>
  )
}

type YearFieldProps = {
  year: number
  years: number[]
  onChange: (year: number) => void
}

/**
 * The year the middle period tab shows. Figma's tab names one year (2024); this picks which,
 * like the map's date picker (map/DatePicker.tsx): the browser's own list lies over the field,
 * invisible, so a click or the keyboard opens it.
 */
function YearField({ year, years, onChange }: YearFieldProps) {
  const id = useId()
  return (
    <div className="controls-panel-year">
      <label htmlFor={id} className="controls-panel-year-label label-ui-s">
        Year
      </label>
      <div className="controls-panel-year-field">
        <span className="label-ui" aria-hidden="true">
          {year}
        </span>
        <Icon name="chevron-down" size={16} />
        <select
          id={id}
          className="controls-panel-year-select"
          value={year}
          onChange={(event) => onChange(Number(event.target.value))}
        >
          {years.map((each) => (
            <option key={each} value={each}>
              {each}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

/**
 * F9: the Controls panel of Figma's frame "Compare models" (node 12:978): which models the
 * chart draws (Toggle rows in each model's chart color), what else it shows, the period, and
 * the latest week of the backtest. Each section opens and closes under its Panel header.
 *
 * Unlike Figma, the Show toggles carry their series' own colors (the threshold amber, the
 * counts grey), so each swatch matches its mark; Figma leaves them all teal, the component's
 * default. Figma's "Upload weekly cases" button is left out: uploading needs a server that
 * refits M4 (the app plan cuts it), so the box names the latest week only.
 */
export default function ControlsPanel({
  models,
  shown,
  onModel,
  layers,
  onLayer,
  period,
  year,
  years,
  onPeriod,
  rangeName,
  latest,
  simulated,
}: ControlsPanelProps) {
  const titleId = useId()
  return (
    <section className="controls-panel" aria-labelledby={titleId}>
      <h2 id={titleId} className="controls-panel-title heading-m">
        Controls
      </h2>
      <Section title="Models" tight>
        {models.map((model) => (
          <ToggleRow
            key={model}
            label={modelStyle(model).name}
            on={shown[model]}
            onChange={(on) => onModel(model, on)}
            color={modelStyle(model).color}
          />
        ))}
      </Section>
      <Section title="Show" tight>
        <ToggleRow
          label={`${rangeName} range`}
          on={layers.range}
          onChange={(on) => onLayer('range', on)}
          color={modelStyle(RANGE_MODEL).color}
        />
        <ToggleRow
          label="Epidemic threshold"
          on={layers.threshold}
          onChange={(on) => onLayer('threshold', on)}
          color="var(--color-status-warn)"
        />
        <ToggleRow
          label="Observed cases"
          on={layers.observed}
          onChange={(on) => onLayer('observed', on)}
          color="var(--color-text-secondary)"
        />
      </Section>
      <Section title="Period">
        <div className="controls-panel-periods">
          <Tab selected={period.kind === 'recent'} onClick={() => onPeriod({ kind: 'recent' })}>
            {`${RECENT_WEEKS} weeks`}
          </Tab>
          <Tab selected={period.kind === 'year'} onClick={() => onPeriod({ kind: 'year', year })}>
            {String(year)}
          </Tab>
          <Tab selected={period.kind === 'all'} onClick={() => onPeriod({ kind: 'all' })}>
            {allYearsName(years)}
          </Tab>
        </div>
        {period.kind === 'year' && (
          <YearField year={year} years={years} onChange={(each) => onPeriod({ kind: 'year', year: each })} />
        )}
      </Section>
      <div className="controls-panel-data">
        <p className="controls-panel-data-label label-eyebrow">Latest week with a count</p>
        <p className="controls-panel-data-week heading-s">{weekTitle(latest)}</p>
        {simulated && <Badge tone="warn">{SIMULATED_LABEL}</Badge>}
      </div>
    </section>
  )
}
