import './Logo.css'

/**
 * F3: the LEPTON logo, Figma component "Logo" (node 3:47): three rising teal bars and the
 * wordmark. It is a picture of the name, so the headers wrap it in a link to the home page
 * that carries the words.
 */
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
