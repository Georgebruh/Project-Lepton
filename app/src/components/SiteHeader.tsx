import { Link, NavLink } from 'react-router'
import Button from './Button.tsx'
import Logo from './Logo.tsx'
import './SiteHeader.css'

/**
 * The header's links, in Figma's order, and the route each one opens. A page's own link reads as
 * the current page (Figma Home: "Overview"); Sources is a part of How it works, so it never does.
 */
const LINKS = [
  { label: 'Overview', to: '/', page: true },
  { label: 'Leptospirosis', to: '/leptospirosis', page: true },
  { label: 'How it works', to: '/how-it-works', page: true },
  { label: 'Results', to: '/map/quezon-city/compare?data=real', page: true },
  { label: 'Sources', to: '/how-it-works#sources', page: false },
]

/**
 * F3: the Figma component "Site header" (node 4:21), the header of the pages for the public:
 * Home, Leptospirosis and How it works. The logo goes home and Try LEPTON opens the map. The
 * map has no header (F14): its logo sits in its top left corner (screens/MapLayout.tsx). Results
 * opens Compare models in the map's city panel, on the real data.
 *
 * F6: the open page's link is in the primary text color, as in the Figma Home frame. Below
 * 1024 px the links move to a row of their own under the logo and the button.
 */
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
