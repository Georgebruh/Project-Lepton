import type { CSSProperties } from 'react'
import { RANGE_MODEL, modelStyle } from './models.ts'
import './SeriesKey.css'

/** The key's line is 16 px long, room for a dash pattern (Figma's keys are 12 px solid lines). */
const KEY_LENGTH = 16

type SeriesKeyProps = {
  /** A model's name in city_forecast.json, or "observed", "range" or "threshold". */
  series: string
}

/**
 * F9: a series' key, drawn like its mark on the chart (dataviz: a line for a line, a block for
 * bars or an area): a model's line in its color and dash, a grey block for the counts, a pale
 * teal block for M4's range, the amber dashed line for the threshold. Figma's chart (node
 * 12:1011) draws them beside each series' name; decoration, hidden from screen readers.
 */
export default function SeriesKey({ series }: SeriesKeyProps) {
  if (series === 'observed') {
    return <span className="series-key-block series-key-observed" aria-hidden="true" />
  }
  if (series === 'range') {
    const style = { '--series-key-color': modelStyle(RANGE_MODEL).color } as CSSProperties
    return <span className="series-key-block series-key-range" style={style} aria-hidden="true" />
  }
  const threshold = series === 'threshold'
  const model = modelStyle(series)
  return (
    <svg
      className={threshold ? 'series-key-line series-key-threshold' : 'series-key-line'}
      width={KEY_LENGTH}
      height={8}
      aria-hidden="true"
      focusable="false"
    >
      <line
        x1={0}
        y1={4}
        x2={KEY_LENGTH}
        y2={4}
        style={threshold ? undefined : { stroke: model.color, strokeWidth: Math.min(2, model.width) }}
        strokeDasharray={threshold ? undefined : model.dash}
      />
    </svg>
  )
}
