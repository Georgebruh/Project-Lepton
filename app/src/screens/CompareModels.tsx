import { useState } from 'react'
import { useLoaderData, useSearchParams } from 'react-router'
import AppBar from '../components/AppBar.tsx'
import CompareChart from '../compare/CompareChart.tsx'
import type { loadCompareData } from '../compare/compareData.ts'
import ControlsPanel from '../compare/ControlsPanel.tsx'
import { modelStyle, toggleOrder } from '../compare/models.ts'
import {
  backtestYears,
  parsePeriod,
  periodName,
  periodParam,
  periodSpan,
  periodTicks,
  periodWeeks,
  stormsIn,
  type Period,
} from '../compare/periods.ts'
import type { Layers } from '../compare/readout.ts'
import ScoreTable from '../compare/ScoreTable.tsx'
import { rangePercent } from '../map/forecast.ts'
import './CompareModels.css'

/**
 * Compare models (route /compare), task F9, from the Figma frame "Compare models" (node 12:966)
 * and its notes (34:365). Figma draws the app bar and the Controls panel; the room beside them
 * holds the chart drawn for this page in How it works (node 12:1010) and, under it, the scores.
 *
 * Reads, through the route's loader (compare/compareData.ts): city_forecast.json, storms.json
 * and, beside B10's real run only, scores.json, all written by F2 (python -m src.app_data).
 * While city_forecast.json says simulated, the chart and the latest week carry the amber badge
 * and every score shows "—": nothing on the page reads as a real result.
 *
 * The period is kept in the address (?period=12w, ?period=2024, ?period=all; the latest year
 * without one), so a link opens the same view. The toggles start as in Figma: M4 and M3 on, the
 * 90% range, the threshold and the counts shown.
 */
export default function CompareModels() {
  const { forecast, storms, scores } = useLoaderData<typeof loadCompareData>()
  const [searchParams, setSearchParams] = useSearchParams()
  const years = backtestYears(forecast)
  const period = parsePeriod(searchParams.get('period'), years)
  const models = toggleOrder(forecast.models)
  const [shown, setShown] = useState(() => Object.fromEntries(models.map((model) => [model, modelStyle(model).on])))
  const [layers, setLayers] = useState<Layers>({ range: true, threshold: true, observed: true })
  // The year the year tab opens: the one in the address, then the last one picked
  const [year, setYear] = useState(period.kind === 'year' ? period.year : years[years.length - 1])

  /** A new period replaces the address's (no new history entry); the page keeps its scroll. */
  function choosePeriod(next: Period) {
    if (next.kind === 'year') {
      setYear(next.year)
    }
    setSearchParams(
      (params) => {
        params.set('period', periodParam(next))
        return params
      },
      { replace: true, preventScrollReset: true },
    )
  }

  const weeks = periodWeeks(forecast, period)
  const span = periodSpan(forecast, period, weeks)
  const rangeName = rangePercent(forecast)
  const name = periodName(period, years)
  return (
    <div className="compare-models">
      <AppBar />
      <main className="compare-models-main">
        <h1 className="visually-hidden">Compare models: Quezon City’s weekly leptospirosis forecasts</h1>
        <ControlsPanel
          models={models}
          shown={shown}
          onModel={(model, on) => setShown({ ...shown, [model]: on })}
          layers={layers}
          onLayer={(layer, on) => setLayers({ ...layers, [layer]: on })}
          period={period}
          year={period.kind === 'year' ? period.year : year}
          years={years}
          onPeriod={choosePeriod}
          rangeName={rangeName}
          latest={forecast.weeks[forecast.weeks.length - 1]}
          simulated={forecast.simulated}
        />
        <div className="compare-models-results">
          <CompareChart
            weeks={weeks}
            span={span}
            ticks={periodTicks(forecast, period, span, years)}
            tickAnchor={period.kind === 'recent' ? 'middle' : 'start'}
            storms={stormsIn(forecast, storms, span)}
            models={models.filter((model) => shown[model])}
            layers={layers}
            periodName={name}
            rangeName={rangeName}
            horizonWeeks={forecast.horizon_weeks}
            covidYears={forecast.covid_years}
            simulated={forecast.simulated}
          />
          <ScoreTable models={forecast.models} ours={forecast.map_model} scores={scores} />
        </div>
      </main>
    </div>
  )
}
