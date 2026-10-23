import { useState } from 'react'
import { SIMULATED_LABEL, formatCount, thresholdCount } from '../map/forecast.ts'
import type { ForecastWeek } from '../map/mapData.ts'
import { RANGE_MODEL, modelStyle } from './models.ts'
import { weekTitle, type Layers } from './readout.ts'
import './WeeksTable.css'

type WeeksTableProps = {
  /** The period's weeks, oldest first. */
  weeks: ForecastWeek[]
  /** The models the chart draws, in the toggles' order. */
  models: string[]
  layers: Layers
  /** The range's name in words, "90%". */
  rangeName: string
  /** The period in words, as the chart's title ends: "2024". */
  periodName: string
  simulated: boolean
}

/**
 * F9: the chart's numbers as a table, under it (dataviz: every chart has a table view, so no
 * number needs the pointer, and a screen reader can read every week). It shows the same weeks
 * and series as the chart, and is built only when opened: the whole backtest is 456 weeks.
 */
export default function WeeksTable({ weeks, models, layers, rangeName, periodName, simulated }: WeeksTableProps) {
  const [open, setOpen] = useState(false)
  const range = layers.range && models.includes(RANGE_MODEL)
  return (
    <details className="weeks-table" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="weeks-table-summary label-ui">Show the weeks as a table</summary>
      {open && (
        // A region the keyboard can reach, so the weeks scroll without a mouse
        <div className="weeks-table-scroll" role="region" aria-label="The weeks as a table" tabIndex={0}>
          <table className="weeks-table-table body-s">
            <caption className="visually-hidden">
              {`Weekly leptospirosis cases and 1-week-ahead forecasts, Quezon City, ${periodName}`}
              {simulated ? `. ${SIMULATED_LABEL}` : ''}
            </caption>
            <thead>
              <tr>
                <th scope="col">Week</th>
                {models.map((model) => (
                  <th key={model} scope="col">
                    {modelStyle(model).key} forecast
                  </th>
                ))}
                {range && <th scope="col">{`${modelStyle(RANGE_MODEL).key} ${rangeName} range`}</th>}
                {layers.observed && <th scope="col">Cases</th>}
                {layers.threshold && <th scope="col">Epidemic threshold</th>}
              </tr>
            </thead>
            <tbody>
              {weeks.map((week) => (
                <tr key={week.week_index}>
                  <th scope="row">
                    {weekTitle(week)}
                    {week.simulated ? ' (simulated)' : ''}
                  </th>
                  {models.map((model) => (
                    <td key={model}>{formatCount(week.forecasts[model].mu)}</td>
                  ))}
                  {range && <td>{`${week.forecasts[RANGE_MODEL].low}–${week.forecasts[RANGE_MODEL].high}`}</td>}
                  {layers.observed && <td>{week.y === null ? '—' : formatCount(week.y)}</td>}
                  {layers.threshold && <td>{formatCount(thresholdCount(week.threshold))}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  )
}
