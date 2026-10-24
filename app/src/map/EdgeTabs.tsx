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
 * The city panel's tabs, on its right edge like bookmarks (Figma "Edge tabs"), under a round Close button
 * that goes back to the Philippines. They have no words: a control's name shows on hover and is its
 * aria-label. The open tab is not a link, so pressing it again keeps the panel open.
 */
export default function EdgeTabs({ level }: EdgeTabsProps) {
  const { search } = useLocation()
  return (
    <div className="edge-tabs">
      <Link to={MAP_PATHS[1] + levelSearch(1, search)} className="edge-close" aria-label="Close Quezon City">
        <Icon name="close" size={18} />
        <span className="edge-tab-label body-s" aria-hidden="true">
          Close
        </span>
      </Link>
      <nav className="edge-tabs-nav" aria-label="Quezon City's views">
        {TABS.map((tab) => {
          const label = (
            <span className="edge-tab-label body-s" aria-hidden="true">
              {tab.name}
            </span>
          )
          if (tab.level === level) {
            return (
              <span key={tab.level} className="edge-tab edge-tab-open" aria-current="page">
                <Icon name={tab.icon} size={22} />
                <span className="visually-hidden">{tab.name}</span>
                {label}
              </span>
            )
          }
          return (
            <Link
              key={tab.level}
              to={MAP_PATHS[tab.level] + levelSearch(tab.level, search)}
              className="edge-tab"
              aria-label={tab.name}
            >
              <Icon name={tab.icon} size={22} />
              {label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
