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

/** The tooltip of the barangay under the pointer. */
export default function BarangayTooltip({ name, barangay, note, style }: BarangayTooltipProps) {
  return (
    <div className="barangay-tooltip" style={style}>
      <div className="barangay-tooltip-title">
        <p className="barangay-tooltip-name label-ui">{name}</p>
        {barangay?.flagged && <Badge tone="alert">Flagged</Badge>}
      </div>
      <BarangayNumbers barangay={barangay} note={note} />
    </div>
  )
}

type BarangayNumbersProps = {
  /** The barangay's numbers in the run on the map; undefined while no storm is shown. */
  barangay: BarangayRun | undefined
  /** What to say instead while no storm is shown. */
  note: string
}

/** The tooltip's numbers, under the name. */
export function BarangayNumbers({ barangay, note }: BarangayNumbersProps) {
  const units = barangay?.units[PLAN_FLOOD]
  if (!barangay || !units) {
    return <p className="barangay-tooltip-text body-s">{note}</p>
  }
  return (
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
  )
}
