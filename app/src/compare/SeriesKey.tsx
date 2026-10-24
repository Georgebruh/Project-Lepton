import type { CSSProperties } from 'react'
import { RANGE_MODEL, modelStyle } from './models.ts'
import './SeriesKey.css'

/** The key's line is 16 px long, room for a dash pattern. */
const KEY_LENGTH = 16

type SeriesKeyProps = {
  /** A model's name in city_forecast.json, or "observed", "range" or "threshold". */
  series: string
}

/** A series' key, drawn like its mark on the chart. */
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
