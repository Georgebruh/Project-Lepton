import { scaleLinear } from 'd3-scale'
import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
} from 'react'
import Badge from '../components/Badge.tsx'
import { badgeWords, formatCount, formatWeek } from '../map/forecast.ts'
import type { ForecastWeek } from '../map/mapData.ts'
import ChartReadout from './ChartReadout.tsx'
import {
  MARGIN,
  STORM_LABEL_ROOM,
  areaPath,
  axisTop,
  barWidth,
  fittingLabels,
  labelWidth,
  leftMargin,
  linePath,
  placeNames,
  plotHeight,
} from './chartGeometry.ts'
import { RANGE_MODEL, modelStyle } from './models.ts'
import type { Span, StormMark, Tick } from './periods.ts'
import { readoutRows, readoutSentence, type Layers } from './readout.ts'
import SeriesKey from './SeriesKey.tsx'
import WeeksTable from './WeeksTable.tsx'
import './CompareChart.css'

/** The shaded COVID years' label, short enough for the two years at 1440 px. */
const COVID_LABEL = 'COVID years: not scored'

/** The tooltip's distance from the crosshair, px. */
const READOUT_OFFSET = 12

/** Where the x axis's labels and the storms' names sit: px below the plot's foot, above its top. */
const TICK_BASELINE = 22
const TOP_LABEL_BASELINE = -6

type CompareChartProps = {
  /** The period's weeks, oldest first. */
  weeks: ForecastWeek[]
  /** The week indexes the x axis spans. */
  span: Span
  /** The x axis's labels (periodTicks). */
  ticks: Tick[]
  tickAnchor: 'start' | 'middle'
  /** The storms whose flood began in the span. */
  storms: StormMark[]
  /** The models drawn, in the toggles' order. */
  models: string[]
  layers: Layers
  /** The period in words, ending the title: "2024". */
  periodName: string
  /** The range's name, "90%". */
  rangeName: string
  /** How many weeks ahead each forecast was made (city_forecast.json's horizon_weeks: 1). */
  horizonWeeks: number
  /** The COVID years, shaded: forecast, but left out of the headline scores. */
  covidYears: number[]
  simulated: boolean
}

/** The width of an element, px, kept up to date as the page resizes; 0 until it is laid out. */
function useWidth(): [RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) {
      return
    }
    setWidth(element.clientWidth)
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}

/** "made the week before", or "made 2 weeks before" for a longer horizon. */
function horizonWords(weeks: number): string {
  return weeks === 1 ? 'made the week before' : `made ${weeks} weeks before`
}

/** The Compare models chart. */
export default function CompareChart({
  weeks,
  span,
  ticks,
  tickAnchor,
  storms,
  models,
  layers,
  periodName,
  rangeName,
  horizonWeeks,
  covidYears,
  simulated,
}: CompareChartProps) {
  const titleId = useId()
  const summaryId = useId()
  const clipId = `compare-chart-clip-${useId().replace(/[^\w-]/g, '')}`
  const [plotRef, width] = useWidth()
  // The week under the crosshair, by week index, and whether the keyboard put it there
  const [active, setActive] = useState<number | null>(null)
  const [byKeyboard, setByKeyboard] = useState(false)

  const range = layers.range && models.includes(RANGE_MODEL)
  const empty = models.length === 0 && !layers.observed && !layers.threshold

  // The counts axis: the tallest count or forecast drawn, raised for a range end or threshold (axisTop)
  const dataMax = Math.max(
    0,
    ...weeks.flatMap((week) => [layers.observed ? (week.y ?? 0) : 0, ...models.map((model) => week.forecasts[model].mu)]),
  )
  const referenceMax = Math.max(
    0,
    ...weeks.flatMap((week) => [range ? week.forecasts[RANGE_MODEL].high : 0, layers.threshold ? week.threshold : 0]),
  )
  const counts = scaleLinear().domain([0, axisTop(dataMax, referenceMax)]).nice(4)
  const top = counts.domain()[1]
  const countTicks = counts.ticks(4).filter(Number.isInteger)
  // What runs above the top in some week, named in the caption
  const offTop = [
    range && weeks.some((week) => week.forecasts[RANGE_MODEL].high > top) && `${rangeName} range`,
    layers.threshold && weeks.some((week) => week.threshold > top) && 'threshold',
  ].filter((name): name is string => Boolean(name))

  // The plot's box: room on top for the storms' and COVID labels when there are any
  const covidWeeks = weeks.filter((week) => covidYears.includes(week.year))
  const marginTop = MARGIN.top + (storms.length || covidWeeks.length ? STORM_LABEL_ROOM : 0)
  const marginLeft = leftMargin(countTicks.map(formatCount))
  const height = plotHeight(width)
  const plotWidth = Math.max(0, width - marginLeft - MARGIN.right)
  const plotHeightPx = height - marginTop - MARGIN.bottom
  const y = counts.copy().range([plotHeightPx, 0])

  // Weeks across: evenly spaced, the first and last bar inside the plot
  const steps = Math.max(1, span.last - span.first)
  const bar = barWidth(plotWidth / steps)
  const inner = Math.max(0, plotWidth - bar)
  const step = inner / steps
  const x = (index: number) => bar / 2 + (index - span.first) * step
  const point = (week: ForecastWeek, value: number): [number, number] => [x(week.week_index), y(value)]

  const activeWeek = weeks.find((week) => week.week_index === active)
  const rows = activeWeek ? readoutRows(activeWeek, models, layers, rangeName) : []
  const activeStorm = activeWeek && storms.find((storm) => storm.index === activeWeek.week_index)

  /** The week nearest the pointer, from its distance into the plot. */
  function weekAt(clientX: number, box: DOMRect): number {
    const index = span.first + (clientX - box.left - marginLeft - bar / 2) / Math.max(step, Number.EPSILON)
    const first = weeks[0].week_index
    const last = weeks[weeks.length - 1].week_index
    return Math.min(last, Math.max(first, Math.round(index)))
  }

  function onPointer(event: PointerEvent<SVGRectElement>) {
    const box = event.currentTarget.ownerSVGElement?.getBoundingClientRect()
    if (box) {
      setActive(weekAt(event.clientX, box))
      setByKeyboard(false)
    }
  }

  /** A mouse leaving hides the tooltip; a finger lifting does not, so a tap on a phone keeps it. */
  function onPointerLeave(event: PointerEvent<SVGRectElement>) {
    if (event.pointerType === 'mouse' && !byKeyboard) {
      setActive(null)
    }
  }

  /** Arrow keys move a week, Home and End to the first and last, Escape hides the tooltip. */
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const position = weeks.findIndex((week) => week.week_index === active)
    const from = position < 0 ? weeks.length - 1 : position
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, from - 1),
      ArrowRight: Math.min(weeks.length - 1, from + 1),
      Home: 0,
      End: weeks.length - 1,
    }
    if (event.key === 'Escape') {
      setActive(null)
      return
    }
    if (!(event.key in moves)) {
      return
    }
    event.preventDefault()
    setActive(weeks[position < 0 ? from : moves[event.key]].week_index)
    setByKeyboard(true)
  }

  /** Focus from the keyboard (not a click) starts at the latest week. */
  function onFocus(event: FocusEvent<HTMLDivElement>) {
    if (event.currentTarget.matches(':focus-visible')) {
      setActive((current) => current ?? weeks[weeks.length - 1].week_index)
      setByKeyboard(true)
    }
  }

  function onBlur() {
    setActive(null)
    setByKeyboard(false)
  }

  // The tooltip sits beside the crosshair, on the side with more room
  const crosshair = activeWeek ? marginLeft + x(activeWeek.week_index) : 0
  const readoutStyle =
    crosshair < width / 2
      ? { left: crosshair + READOUT_OFFSET, top: marginTop }
      : { right: width - crosshair + READOUT_OFFSET, top: marginTop }

  const xLabels = fittingLabels(
    ticks.map((tick) => ({ ...tick, x: x(tick.index) })),
    tickAnchor,
  )
  const stormNames = placeNames(
    storms.map((storm) => ({ ...storm, x: x(storm.index) })),
    plotWidth + MARGIN.right,
  )
  const covidBand = covidWeeks.length
    ? {
        from: Math.max(0, x(covidWeeks[0].week_index) - step / 2),
        to: Math.min(plotWidth, x(covidWeeks[covidWeeks.length - 1].week_index) + step / 2),
      }
    : null

  const drawn = models.map((model) => modelStyle(model).key)
  // A simulated week still under way has no count
  const counted = weeks.flatMap((week) => (week.y === null ? [] : [week.y]))
  // The badge also when the Simulation mode added some of the weeks
  const simulatedWords = simulated || weeks.some((week) => week.simulated) ? badgeWords(simulated) : null
  const summary =
    `${weeks.length} weeks, ${formatWeek(weeks[0].start, weeks[weeks.length - 1].end)}: ` +
    (counted.length ? `counts from ${formatCount(Math.min(...counted))} to ${formatCount(Math.max(...counted))}, ` : '') +
    `above the epidemic threshold in ${weeks.filter((week) => week.breached).length} weeks.` +
    (drawn.length ? ` Forecasts drawn: ${drawn.join(', ')}.` : '') +
    (simulatedWords ? ` ${simulatedWords}: the counts after QCESD's last week are made up.` : '')

  return (
    <figure className="compare-chart" aria-labelledby={titleId}>
      <div className="compare-chart-header">
        <h2 id={titleId} className="compare-chart-title heading-s">
          Weekly leptospirosis cases, Quezon City · {periodName}
        </h2>
        {simulatedWords && <Badge tone="warn">{simulatedWords}</Badge>}
        <ul className="compare-chart-keys" aria-label="Key">
          {models.map((model) => (
            <li key={model} className="compare-chart-key label-eyebrow">
              <SeriesKey series={model} />
              {modelStyle(model).key}
            </li>
          ))}
          {range && (
            <li className="compare-chart-key label-eyebrow">
              <SeriesKey series="range" />
              {`${modelStyle(RANGE_MODEL).key} ${rangeName} range`}
            </li>
          )}
          {layers.observed && (
            <li className="compare-chart-key label-eyebrow">
              <SeriesKey series="observed" />
              Observed
            </li>
          )}
          {layers.threshold && (
            <li className="compare-chart-key label-eyebrow">
              <SeriesKey series="threshold" />
              Threshold
            </li>
          )}
        </ul>
      </div>

      <div
        ref={plotRef}
        className="compare-chart-plot"
        style={{ height }}
        tabIndex={0}
        role="group"
        aria-label="Chart. Left and right arrow keys move from week to week."
        aria-describedby={summaryId}
        onKeyDown={onKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
      >
        {width > 0 && (
          <svg className="compare-chart-svg" width={width} height={height} aria-hidden="true" focusable="false">
            <defs>
              <clipPath id={clipId}>
                <rect x={-bar} y={0} width={plotWidth + 2 * bar} height={plotHeightPx} />
              </clipPath>
            </defs>
            <g transform={`translate(${marginLeft} ${marginTop})`}>
              {covidBand && (
                <g>
                  <rect
                    className="compare-chart-covid"
                    x={covidBand.from}
                    y={0}
                    width={covidBand.to - covidBand.from}
                    height={plotHeightPx}
                  />
                  {covidBand.to - covidBand.from >= labelWidth(COVID_LABEL) && (
                    <text
                      className="compare-chart-top-label compare-chart-covid-label label-eyebrow"
                      x={(covidBand.from + covidBand.to) / 2}
                      y={TOP_LABEL_BASELINE}
                      textAnchor="middle"
                    >
                      {COVID_LABEL}
                    </text>
                  )}
                </g>
              )}
              {countTicks.map((tick) => (
                <g key={tick}>
                  <rect className="compare-chart-grid" x={0} y={y(tick)} width={plotWidth} height={1} />
                  <text className="compare-chart-axis label-eyebrow" x={-marginLeft} y={y(tick) + 4}>
                    {formatCount(tick)}
                  </text>
                </g>
              ))}
              {xLabels.map((tick) => (
                <text
                  key={tick.index}
                  className="compare-chart-axis label-eyebrow"
                  x={tick.x}
                  y={plotHeightPx + TICK_BASELINE}
                  textAnchor={tickAnchor}
                >
                  {tick.label}
                </text>
              ))}
              {storms.map((storm) => (
                <rect
                  key={storm.storm}
                  className="compare-chart-storm"
                  x={x(storm.index)}
                  y={TOP_LABEL_BASELINE + 2}
                  width={1}
                  height={plotHeightPx - TOP_LABEL_BASELINE - 2}
                />
              ))}
              {stormNames.map((storm) => (
                <text
                  key={storm.storm}
                  className="compare-chart-top-label label-eyebrow"
                  x={storm.textX}
                  y={TOP_LABEL_BASELINE}
                  textAnchor={storm.anchor}
                >
                  {storm.label}
                </text>
              ))}
              {/* The weeks' marks: drawn anew, from the left, for each period */}
              <g key={periodName} className="compare-chart-data">
                {layers.observed &&
                  weeks.map(
                    (week) =>
                      // A week under way has no bar; a simulated week's bar is outlined, not filled
                      week.y !== null && (
                        <rect
                          key={week.week_index}
                          className={[
                            'compare-chart-bar',
                            week.week_index === active && 'compare-chart-bar-active',
                            week.simulated && 'compare-chart-bar-simulated',
                          ]
                            .filter(Boolean)
                            .join(' ')}
                          x={x(week.week_index) - bar / 2}
                          y={y(week.y)}
                          width={bar}
                          height={plotHeightPx - y(week.y)}
                          rx={bar >= 4 ? 1 : 0}
                        />
                      ),
                  )}
                <g clipPath={`url(#${clipId})`}>
                  {range && (
                    <path
                      className="compare-chart-range"
                      style={{ fill: modelStyle(RANGE_MODEL).color }}
                      d={areaPath(
                        weeks.map((week) => point(week, week.forecasts[RANGE_MODEL].high)),
                        weeks.map((week) => point(week, week.forecasts[RANGE_MODEL].low)),
                      )}
                    />
                  )}
                  {layers.threshold && (
                    <path
                      className="compare-chart-threshold"
                      d={linePath(weeks.map((week) => point(week, week.threshold)))}
                    />
                  )}
                  {/* Drawn in reverse, so the first toggle (M4) lies on top */}
                  {[...models].reverse().map((model) => {
                    const style = modelStyle(model)
                    return (
                      <path
                        key={model}
                        className="compare-chart-line"
                        style={{ stroke: style.color, strokeWidth: style.width }}
                        strokeDasharray={style.dash}
                        d={linePath(weeks.map((week) => point(week, week.forecasts[model].mu)))}
                      />
                    )
                  })}
                </g>
              </g>
              <rect className="compare-chart-baseline" x={0} y={plotHeightPx} width={plotWidth} height={1} />
              {activeWeek && (
                <g>
                  <rect
                    className="compare-chart-crosshair"
                    x={x(activeWeek.week_index)}
                    y={0}
                    width={1}
                    height={plotHeightPx}
                  />
                  {models.map((model) => (
                    <circle
                      key={model}
                      className="compare-chart-dot"
                      style={{ fill: modelStyle(model).color }}
                      cx={x(activeWeek.week_index)}
                      cy={Math.max(0, y(activeWeek.forecasts[model].mu))}
                      r={4}
                    />
                  ))}
                </g>
              )}
              {/* The pointer's target: the whole chart, so any point picks the nearest week */}
              <rect
                className="compare-chart-hit"
                x={-marginLeft}
                y={-marginTop}
                width={width}
                height={height}
                onPointerMove={onPointer}
                onPointerDown={onPointer}
                onPointerLeave={onPointerLeave}
              />
            </g>
          </svg>
        )}
        {activeWeek && (
          <ChartReadout week={activeWeek} rows={rows} storm={activeStorm} simulated={simulated} style={readoutStyle} />
        )}
        {empty && <p className="compare-chart-empty body-m">Turn on a model or a series under Controls to draw it.</p>}
      </div>
      <p id={summaryId} className="visually-hidden">
        {summary}
      </p>
      <p className="visually-hidden" aria-live="polite">
        {byKeyboard && activeWeek ? readoutSentence(activeWeek, rows, activeStorm, simulated) : ''}
      </p>

      <figcaption className="compare-chart-caption body-s">
        {`Each line is a model's forecast of the week's cases, ${horizonWords(horizonWeeks)}.`}
        {covidBand && ` The shaded weeks are the COVID years ${covidYears.join('–')}: forecast, but left out of the scores.`}
        {offTop.length > 0 &&
          ` In some weeks the ${offTop.join(' and the ')} ${offTop.length > 1 ? 'run' : 'runs'} above the top of the chart; point at a week for its numbers.`}
      </figcaption>
      <WeeksTable
        weeks={weeks}
        models={models}
        layers={layers}
        rangeName={rangeName}
        periodName={periodName}
        simulated={simulated}
      />
    </figure>
  )
}
