import './StatCard.css'

type StatCardProps = {
  /** What the number counts, e.g. "Residents exposed". */
  label: string
  /** The number, already formatted, e.g. "425,192". */
  value: string
  /** Where the number comes from, e.g. "Severe Tropical Storm Kristine, Oct 2024 · observed rain". */
  caption?: string
}

/**
 * F3: the Figma component "Stat card" (node 4:8): one headline number with its label and
 * source. It fills the width of its container (Figma draws it 320 px wide).
 */
export default function StatCard({ label, value, caption }: StatCardProps) {
  return (
    <div className="stat-card">
      <p className="stat-card-label label-eyebrow">{label}</p>
      <p className="stat-card-value data-xl">{value}</p>
      {caption && <p className="stat-card-caption body-s">{caption}</p>}
    </div>
  )
}
