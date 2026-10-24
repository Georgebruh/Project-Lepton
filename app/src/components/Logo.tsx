import './Logo.css'

/** The LEPTON logo: the wordmark with a ripple for its O. */
export default function Logo() {
  return (
    <span className="logo">
      <span className="visually-hidden">LEPTON</span>
      <span className="logo-word" aria-hidden="true">
        LEPT
        <svg className="logo-o" viewBox="0 0 48 48">
          <path className="logo-o-ring" d={RING} />
          <circle className="logo-o-dot" cx="24" cy="24" r="5" />
        </svg>
        N
      </span>
    </span>
  )
}

/** The ring of the O on a 48 px grid: a circle of radius 16 with a ripple. */
function ringPath(): string {
  const points: string[] = []
  for (let i = 0; i <= 360; i++) {
    const angle = (i / 360) * 2 * Math.PI
    const radius = 16 + 1.2 * Math.cos(14 * angle)
    const x = 24 + radius * Math.cos(angle)
    const y = 24 + radius * Math.sin(angle)
    points.push(`${x.toFixed(2)} ${y.toFixed(2)}`)
  }
  return `M${points.join('L')}Z`
}

const RING = ringPath()
