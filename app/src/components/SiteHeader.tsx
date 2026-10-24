import { Link, NavLink } from 'react-router'
import Button from './Button.tsx'
import Logo from './Logo.tsx'
import './SiteHeader.css'

/** The header's links, in order, and the route each one opens. */
const LINKS = [
  { label: 'Overview', to: '/', page: true },
  { label: 'Leptospirosis', to: '/leptospirosis', page: true },
  { label: 'How it works', to: '/how-it-works', page: true },
  { label: 'Results', to: '/map/quezon-city/compare?data=real', page: true },
  { label: 'Sources', to: '/how-it-works#sources', page: false },
]

/** The "Site header" component, the header of the pages for the public. */
export default function SiteHeader() {
  return (
    <header className="site-header">
      <Link to="/" className="site-header-home" aria-label="LEPTON, home page">
        <Logo />
      </Link>
      <nav className="site-header-nav" aria-label="Main">
        {LINKS.map(({ label, to, page }) =>
          page ? (
            <NavLink key={label} to={to} end className="site-header-link label-ui">
              {label}
            </NavLink>
          ) : (
            <Link key={label} to={to} className="site-header-link label-ui">
              {label}
            </Link>
          ),
        )}
      </nav>
      <Button variant="secondary" icon="arrow-right" to="/map" className="site-header-cta">
        Try LEPTON
      </Button>
    </header>
  )
}
