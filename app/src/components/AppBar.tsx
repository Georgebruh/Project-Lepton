import { Link } from 'react-router'
import Badge from './Badge.tsx'
import Button from './Button.tsx'
import Logo from './Logo.tsx'
import Tab from './Tab.tsx'
import './AppBar.css'

/**
 * F3: the app bar of the map and Compare models screens, from the Figma frame "Map · 1 Metro
 * Manila" (node 55:319). The views Map and Compare models are tabs, selected on their own
 * routes; Methods opens How it works. The "Stock planning, not prescriptions" badge stays on
 * every screen that shows doses.
 *
 * Figma also has a City outlook tab and an Upload weekly cases button. They stay hidden until
 * both are designed and built: City outlook has no screen, and uploading cases needs a server
 * that refits M4 (the app plan's Screens section).
 *
 * F11: below 768 px the bar takes two rows, the logo and the badge over the views and Methods,
 * so nothing scrolls sideways on a phone (AppBar.css).
 */
export default function AppBar() {
  return (
    <header className="app-bar">
      <Link to="/" className="app-bar-home" aria-label="LEPTON, home page">
        <Logo />
      </Link>
      <span className="app-bar-divider" aria-hidden="true" />
      <nav className="app-bar-views" aria-label="Views">
        <Tab to="/map">Map</Tab>
        <Tab to="/compare">Compare models</Tab>
      </nav>
      <Badge tone="warn" className="app-bar-badge">
        Stock planning, not prescriptions
      </Badge>
      <Button variant="ghost" to="/how-it-works" className="app-bar-methods">
        Methods
      </Button>
    </header>
  )
}
