import './CenterRow.css'

type CenterRowProps = {
  /** The health center's name. */
  name: string
  /** Doxycycline 100 mg capsules. */
  doxycycline: number
  /** Children's courses. */
  courses: number
  /** Amoxicillin 500 mg tablets, for pregnant women. */
  amoxicillin: number
}

/** Writes a count with thousands separators: 92935 → "92,935". */
function formatCount(n: number): string {
  return n.toLocaleString('en-US')
}

/** The "Center row" component: one health center's stock need, in the prophylaxis panel's list. */
export default function CenterRow({ name, doxycycline, courses, amoxicillin }: CenterRowProps) {
  return (
    <div className="center-row" role="row">
      <span className="center-row-name body-s" role="cell">
        {name}
      </span>
      <span className="center-row-doxycycline data-m" role="cell">
        {formatCount(doxycycline)}
      </span>
      <span className="center-row-courses data-m" role="cell">
        {formatCount(courses)}
      </span>
      <span className="center-row-amoxicillin data-m" role="cell">
        {formatCount(amoxicillin)}
      </span>
    </div>
  )
}

/** The row of column headers above center rows, as in Home's stock list. */
export function CenterRowHeader() {
  return (
    <div className="center-row center-row-header" role="row">
      <span className="center-row-name body-s" role="columnheader">
        Health center
      </span>
      <span className="center-row-doxycycline data-m" role="columnheader" aria-label="Doxycycline 100 mg capsules">
        Doxy
      </span>
      <span className="center-row-courses data-m" role="columnheader" aria-label="Children's courses">
        Child
      </span>
      <span className="center-row-amoxicillin data-m" role="columnheader" aria-label="Amoxicillin 500 mg tablets">
        Amox
      </span>
    </div>
  )
}
