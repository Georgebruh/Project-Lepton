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

/**
 * F3: the Figma component "Center row" (node 4:12): one health center's stock need, in the
 * prophylaxis panel's list (F5). The columns are doxycycline capsules, children's courses and
 * amoxicillin tablets, as whole units. Each row is a table row for screen readers
 * (role="row"), so put the rows in an element with role="table" whose first row holds the
 * column headers (role="columnheader").
 */
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
