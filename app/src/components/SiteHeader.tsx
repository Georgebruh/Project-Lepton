import { Link, useLocation } from 'react-router'
import Button from './Button.tsx'
import Logo from './Logo.tsx'
import './SiteHeader.css'

/** The header's links, in Figma's order, and the route each one opens. */
const LINKS = [
  { label: 'Overview', to: '/' },
  { label: 'Leptospirosis', to: '/leptospirosis' },
  { label: 'How it works', to: '/how-it-works' },
  { label: 'Results', to: '/compare' },
  { label: 'Sources', to: '/how-it-works#sources' },
]

/**
 * F3: the Figma component "Site header" (node 4:21), the header of the pages for the public:
 * Home, Leptospirosis and How it works. The logo goes home and Try LEPTON opens the map. The
 * map screens use the AppBar instead.
 *
 * F7: the link to the page being read is marked as the current page and drawn in the
 * primary text color, as the Leptospirosis frame (38:278) shows. Sources, which opens a part
 * of How it works, is never the current page.
 */
export default function SiteHeader() {
  const { pathname } = useLocation()
  return (
    <header className="site-header">
      <Link to="/" className="site-header-home" aria-label="LEPTON, home page">
        <Logo />
      </Link>
      <nav className="site-header-nav" aria-label="Main">
        {LINKS.map(({ label, to }) => (
          <Link
            key={label}
            to={to}
            className="site-header-link label-ui"
            aria-current={to === pathname ? 'page' : undefined}
          >
            {label}
          </Link>
        ))}
      </nav>
      <Button variant="secondary" icon="arrow-right" to="/map">
        Try LEPTON
      </Button>
    </header>
  )
}
