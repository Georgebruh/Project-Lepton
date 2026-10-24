import './Logo.css'

/** The LEPTON logo, the "Logo" component: three rising teal bars and the wordmark. */
export default function Logo() {
  return (
    <span className="logo">
      <span className="logo-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className="logo-word">LEPTON</span>
    </span>
  )
}
