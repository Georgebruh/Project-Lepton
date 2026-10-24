import { Link, useLocation } from 'react-router'
import Icon, { type IconName } from '../components/Icon.tsx'
import { MAP_PATHS, levelSearch, type MapLevel } from './routes.ts'
import './EdgeTabs.css'

/** The panel's two tabs: the level each opens, its icon and its name. */
const TABS: { level: MapLevel; icon: IconName; name: string }[] = [
  { level: 2, icon: 'cases', name: 'Cases forecast' },
  { level: 3, icon: 'capsule', name: 'Prophylaxis plan' },
]

type EdgeTabsProps = {
  /** The open level: its tab joins the panel. */
  level: MapLevel
}

/**
 * The city panel's tabs, on its right edge like bookmarks (Figma "Edge tabs"). They have no words: a tab's
 * name shows on hover and is its aria-label. The open tab closes the panel: it goes back to the Philippines.
 */
export default function EdgeTabs({ level }: EdgeTabsProps) {
  const { search } = useLocation()
  return (
    <nav className="edge-tabs" aria-label="Quezon City's views">
      {TABS.map((tab) => {
        const open = tab.level === level
        const to = open ? MAP_PATHS[1] + levelSearch(1, search) : MAP_PATHS[tab.level] + levelSearch(tab.level, search)
        return (
          <Link
            key={tab.level}
            to={to}
            className={open ? 'edge-tab edge-tab-open' : 'edge-tab'}
            aria-label={open ? `Close the ${tab.name.toLowerCase()}` : tab.name}
            aria-current={open ? 'page' : undefined}
          >
            <Icon name={tab.icon} size={22} />
            <span className="edge-tab-label body-s" aria-hidden="true">
              {open ? 'Close' : tab.name}
            </span>
          </Link>
        )
      })}
    </nav>
  )
}
