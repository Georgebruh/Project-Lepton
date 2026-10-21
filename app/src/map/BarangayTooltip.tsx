import type { CSSProperties } from 'react'
import Badge from '../components/Badge.tsx'
import { formatCount } from './forecast.ts'
import { PLAN_FLOOD, formatShare } from './plan.ts'
import type { BarangayRun } from './planData.ts'
import './BarangayTooltip.css'

type BarangayTooltipProps = {
  /** The barangay's name. */
  name: string
  /** Its numbers in the run on the map; undefined while no storm is shown. */
  barangay: BarangayRun | undefined
  /** What the tooltip says while no storm is shown, e.g. "No storm forecast for this date." */
  note: string
  /** Its place over the map (placeTooltip). */
  style: CSSProperties
}

/**
 * F5: the tooltip of the barangay under the pointer, Figma frame 3a (node 57:1020): its name,
 * the Flagged badge if it is flagged, its residents exposed and their share, then its three
 * units for the plan's flood (D = 1, w = 0.5). The units sit above the "Stock planning, not
 * prescriptions" badge (app check U2, which looks at the tooltips too); Figma's 3a has none.
 */
export default function BarangayTooltip({ name, barangay, note, style }: BarangayTooltipProps) {
  const units = barangay?.units[PLAN_FLOOD]
  return (
    <div className="barangay-tooltip" style={style}>
      <div className="barangay-tooltip-title">
        <p className="barangay-tooltip-name label-ui">{name}</p>
        {barangay?.flagged && <Badge tone="alert">Flagged</Badge>}
      </div>
      {barangay && units ? (
        <>
          <p className="barangay-tooltip-text body-s">
            {`${formatCount(barangay.exposed)} of ${formatCount(barangay.pop_2024)} residents exposed ` +
              `(${formatShare(barangay.share)})`}
          </p>
          <hr className="barangay-tooltip-divider" />
          <dl className="barangay-tooltip-units body-s">
            <div>
              <dt>Doxycycline 100 mg capsules</dt>
              <dd className="data-m">{formatCount(units.doxy100)}</dd>
            </div>
            <div>
              <dt>Children's courses</dt>
              <dd className="data-m">{formatCount(units.courses)}</dd>
            </div>
            <div>
              <dt>Amoxicillin 500 mg tablets</dt>
              <dd className="data-m">{formatCount(units.amox500)}</dd>
            </div>
          </dl>
          <Badge tone="warn" className="barangay-tooltip-badge">
            Stock planning, not prescriptions
          </Badge>
        </>
      ) : (
        <p className="barangay-tooltip-text body-s">{note}</p>
      )}
    </div>
  )
}
