import { useId } from 'react'
import StatCard from '../components/StatCard.tsx'
import type { ModelScores, Scores } from './compareData.ts'
import { modelStyle } from './models.ts'
import { yearsWords } from './periods.ts'
import './ScoreTable.css'

/** What a score shows while there is none: the forecasts are simulated (the Design notes: "—"). */
const NONE = '—'

/**
 * D5's comparison, as the plan fixes it (config.PRIMARY_COMPARISON): M4 against M3. While the
 * forecasts are simulated there is no scores.json to name them, so the label names them here.
 */
const PRIMARY_LABEL = 'Primary result · M4 against M3'

/** The table's columns: each score's key in scores.json, its heading, and how it is written. */
const COLUMNS: { key: keyof ModelScores; heading: string; format: (value: number) => string }[] = [
  { key: 'mae', heading: 'MAE', format: (value) => fixed(value, 1) },
  { key: 'mase', heading: 'MASE', format: (value) => fixed(value, 2) },
  { key: 'wis', heading: 'WIS', format: (value) => fixed(value, 1) },
  { key: 'coverage_90', heading: '90% coverage', format: (value) => `${Math.round(value * 100)}%` },
  { key: 'brier', heading: 'Brier score', format: (value) => fixed(value, 3) },
]

/** A number with `digits` decimals and thousands separators: 1,234.5. */
function fixed(value: number, digits: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** A difference with its sign, as D8's figure 2 writes it (2 decimals): "−1.23", "+0.40", "0.00". */
function signed(value: number): string {
  const text = fixed(Math.abs(value), 2)
  if (Number(text) === 0) {
    return text
  }
  return `${value < 0 ? '−' : '+'}${text}`
}

type ScoreTableProps = {
  /** The models, in city_forecast.json's order, which is D8's figure 2's: M0, M1, M3, M4, M4 without EI2. */
  models: string[]
  /** LEPTON's model, whose row is tinted as in Figma's models table (city_forecast.json's map_model, M4). */
  ours: string
  /** The real run's scores; null while the forecasts are simulated. */
  scores: Scores | null
}

/**
 * F9: the scores under the chart, from scores.json (F2): the primary result, D5's mean of
 * |error M4| - |error M3| with its 95% interval, as a Stat card, and each model's MAE, MASE, WIS,
 * 90% coverage and Brier score. Figma's frame leaves this room empty; the table follows its
 * How it works models table (node 12:1482), LEPTON's row tinted.
 *
 * F2 writes scores.json beside B10's real run only, so while the forecasts are simulated every
 * score shows "—" and nothing here reads as a result. After the real run the numbers equal D8's
 * figure 2 table (results/d8_fig2_mae.csv): its MAE by model and its 8-week "M4 vs M3" row
 * (check "F9 scores" in python -m src.checks).
 */
export default function ScoreTable({ models, ours, scores }: ScoreTableProps) {
  const titleId = useId()
  const noteId = useId()
  const primary = scores?.primary
  const caption = primary
    ? `Cases a week, over ${primary.weeks} weeks: M4's miss minus M3's, on average. 95% interval ` +
      `${signed(primary.low)} to ${signed(primary.high)}: ${primary.verdict}.`
    : 'Shown once LEPTON runs on Quezon City’s weekly case counts.'
  const note = scores
    ? `MAE and MASE over ${yearsWords(scores.windows.mae_mase)}; WIS, 90% coverage and the Brier score over ` +
      `${yearsWords(scores.windows.wis_coverage_brier)}. The COVID years are left out, whatever period the chart shows.`
    : 'No scores yet: the forecasts above are simulated. Each model is scored once LEPTON’s backtest runs on ' +
      'Quezon City’s weekly case counts from QCESD.'
  const blocks = primary ? `${primary.block_weeks}-week blocks` : 'blocks of weeks'

  return (
    <section className="score-table" aria-labelledby={titleId}>
      <h2 id={titleId} className="score-table-title heading-m">
        Scores
      </h2>
      <div className="score-table-body">
        <div className="score-table-primary">
          <StatCard label={PRIMARY_LABEL} value={primary ? signed(primary.mean_diff) : NONE} caption={caption} />
        </div>
        {/* A region the keyboard can reach, so a phone's reader can scroll the table sideways */}
        <div className="score-table-scroll" role="region" aria-label="Scores by model" tabIndex={0}>
          <table className="score-table-table" aria-describedby={noteId}>
            <thead>
              <tr className="label-eyebrow">
                <th scope="col">Model</th>
                {COLUMNS.map((column) => (
                  <th key={column.key} scope="col">
                    {column.heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {models.map((model) => {
                const row = scores?.models[model]
                return (
                  <tr key={model} className={model === ours ? 'score-table-ours' : undefined}>
                    <th scope="row" className="heading-s">
                      {modelStyle(model).name}
                    </th>
                    {COLUMNS.map((column) => (
                      <td key={column.key} className="body-m">
                        {row ? column.format(row[column.key]) : NONE}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p id={noteId} className="score-table-note body-s">
        {note}
      </p>
      <dl className="score-table-words body-s">
        <div>
          <dt>MAE</dt>
          <dd>Mean absolute error: the average miss, in cases a week. Lower is better.</dd>
        </div>
        <div>
          <dt>MASE</dt>
          <dd>The MAE divided by the average miss of guessing “same week last year” before the backtest. Below 1 beats that guess.</dd>
        </div>
        <div>
          <dt>WIS</dt>
          <dd>Weighted interval score: the whole forecast, its ranges’ width and how far the count fell outside them, in cases. Lower is better.</dd>
        </div>
        <div>
          <dt>90% coverage</dt>
          <dd>How often the count fell inside the 90% range: about 90% when the range is sized right.</dd>
        </div>
        <div>
          <dt>Brier score</dt>
          <dd>The average squared gap between the chance of an outbreak and what happened (1 if the count crossed the threshold, 0 if not). 0 is perfect.</dd>
        </div>
        <div>
          <dt>Primary result</dt>
          <dd>{`Each week, M4’s miss minus M3’s, averaged: below 0, M4 misses less. Its 95% interval comes from resampling the weeks in ${blocks} (a moving-block bootstrap).`}</dd>
        </div>
      </dl>
    </section>
  )
}
