import { useState } from 'react'
import { useLoaderData, useSearchParams } from 'react-router'
import CompareChart from '../compare/CompareChart.tsx'
import { scoresFor, type loadCompareData } from '../compare/compareData.ts'
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
import { useMapContext } from '../map/mapContext.ts'
import PanelModes from '../map/PanelModes.tsx'
import './MapCompare.css'

/** Compare models in the city panel (route /map/quezon-city/compare, map level 2). */
export default function MapCompare() {
  const { forecast } = useMapContext()
  const { storms, scores } = useLoaderData<typeof loadCompareData>()
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
  const counted = forecast.weeks.filter((week) => week.y !== null)
  return (
    <div className="map-compare">
      <PanelModes mode="compare" />
      <div className="map-compare-heading">
        {/* Takes the keyboard when the city opens (MapLayout) */}
        <h2 className="map-compare-title heading-l" tabIndex={-1}>
          Quezon City
        </h2>
        <p className="map-compare-subtitle label-ui-s">Compare models · weekly cases, 1 week ahead</p>
      </div>
      <div className="map-compare-results">
        <CompareChart
          weeks={weeks}
          span={span}
          ticks={periodTicks(forecast, period, span, years)}
          tickAnchor={period.kind === 'recent' ? 'middle' : 'start'}
          storms={stormsIn(forecast, storms, span)}
          models={models.filter((model) => shown[model])}
          layers={layers}
          periodName={periodName(period, years)}
          rangeName={rangeName}
          horizonWeeks={forecast.horizon_weeks}
          covidYears={forecast.covid_years}
          simulated={forecast.simulated}
        />
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
          latest={counted[counted.length - 1]}
          simulated={forecast.simulated}
        />
        <ScoreTable models={forecast.models} ours={forecast.map_model} scores={scoresFor(forecast, scores)} />
      </div>
    </div>
  )
}
