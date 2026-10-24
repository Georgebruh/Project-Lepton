import { classLabel, flagLine } from './plan.ts'
import type { ShareClass } from './planData.ts'
import './ExposureLegend.css'

type ExposureLegendProps = {
  /** The map's five classes of share, lightest first (storms.json). */
  classes: ShareClass[]
  /** The share at which a barangay is flagged (0.25). */
  flagShare: number
}

/** The map's legend at level 3. */
export default function ExposureLegend({ classes, flagShare }: ExposureLegendProps) {
  return (
    <div className="exposure-legend">
      <p className="exposure-legend-title label-ui-s">Share of residents exposed to floodwater</p>
      <ul className="exposure-legend-ramp body-s">
        {classes.map((share) => (
          <li key={share.class}>
            <span className={`exposure-legend-swatch exposure-legend-swatch-${share.class}`} aria-hidden="true" />
            {classLabel(share, classes)}
          </li>
        ))}
      </ul>
      <p className="exposure-legend-flag body-s">{flagLine(classes, flagShare)}</p>
    </div>
  )
}
