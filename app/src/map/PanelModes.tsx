import { useLocation } from 'react-router'
import Tab from '../components/Tab.tsx'
import { MAP_PATHS, levelSearch } from './routes.ts'
import './PanelModes.css'

type PanelModesProps = {
  /** The panel showing: Quezon City's case forecast (F4) or its prophylaxis plan (F5). */
  mode: 'cases' | 'prophylaxis'
}

/**
 * F4: the two modes at the top of the city panel, Figma "Modes" in frames 2 and 3: tabs that
 * open the case forecast and the prophylaxis plan, keeping the chosen date (levelSearch). The
 * selected tab comes from `mode`, not the address, so it stays selected while the panel slides
 * away.
 */
export default function PanelModes({ mode }: PanelModesProps) {
  const { search } = useLocation()
  return (
    <nav className="panel-modes" aria-label="Quezon City">
      <Tab to={MAP_PATHS[2] + levelSearch(2, search)} selected={mode === 'cases'}>
        Cases forecast
      </Tab>
      <Tab to={MAP_PATHS[3] + levelSearch(3, search)} selected={mode === 'prophylaxis'}>
        Prophylaxis plan
      </Tab>
    </nav>
  )
}
