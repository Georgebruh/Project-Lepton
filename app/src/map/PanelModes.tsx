import { Link, useLocation } from 'react-router'
import Icon from '../components/Icon.tsx'
import Tab from '../components/Tab.tsx'
import { COMPARE_PATH, MAP_PATHS, levelSearch } from './routes.ts'
import './PanelModes.css'

type PanelModesProps = {
  /** The panel showing: Quezon City's case forecast (F4), Compare models (F14) or its prophylaxis plan (F5). */
  mode: 'cases' | 'compare' | 'prophylaxis'
}

/**
 * F4: the modes at the top of the city panel, Figma "Modes" in frames 2 and 3: tabs that open
 * the case forecast and the prophylaxis plan, keeping the chosen date (levelSearch). The
 * selected tab comes from `mode`, not the address, so it stays selected while the panel slides
 * away.
 *
 * F14: Compare models is a tab here too (it was its own screen, F9), and a Close button at the
 * end of the row goes back to the Philippines, as the breadcrumb's Back did.
 */
export default function PanelModes({ mode }: PanelModesProps) {
  const { search } = useLocation()
  return (
    <div className="panel-modes">
      <nav className="panel-modes-tabs" aria-label="Quezon City">
        <Tab to={MAP_PATHS[2] + levelSearch(2, search)} selected={mode === 'cases'}>
          Cases forecast
        </Tab>
        <Tab to={COMPARE_PATH + levelSearch(2, search)} selected={mode === 'compare'}>
          Compare models
        </Tab>
        <Tab to={MAP_PATHS[3] + levelSearch(3, search)} selected={mode === 'prophylaxis'}>
          Prophylaxis plan
        </Tab>
      </nav>
      <Link to={MAP_PATHS[1] + levelSearch(1, search)} className="panel-modes-close" aria-label="Close, back to the map">
        <Icon name="close" size={18} />
      </Link>
    </div>
  )
}
