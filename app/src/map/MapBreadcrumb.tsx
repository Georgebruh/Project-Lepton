import { Link, useLocation } from 'react-router'
import Icon from '../components/Icon.tsx'
import DatePicker from './DatePicker.tsx'
import { MAP_PATHS, levelSearch, type MapLevel } from './routes.ts'
import './MapBreadcrumb.css'

/** The map's levels as the breadcrumb names them. */
const STEPS: { level: MapLevel; name: string }[] = [
  { level: 1, name: 'Metro Manila' },
  { level: 2, name: 'Quezon City' },
  { level: 3, name: 'Prophylaxis plan' },
]

type MapBreadcrumbProps = {
  /** The open level. */
  level: MapLevel
  /** The chosen date and the dates the picker offers. */
  date: string
  first: string
  last: string
  /** Called with each new date the reader picks. */
  onDateChange: (day: string) => void
}

/**
 * F4: the bar under the app bar on every map level, Figma "Breadcrumb" (nodes 55:369, 53:299
 * and 56:446): Back to the level above ("All cities" from Quezon City), the trail from Metro
 * Manila to the open level, and the date picker. Links keep the chosen date (and, out of the
 * prophylaxis plan, put back the date from before a storm opened from its list: levelSearch).
 *
 * F11: below 768 px the trail hides below level 1, so Back and the date picker fit a phone:
 * Back names the level above, and the panel's heading the open one.
 */
export default function MapBreadcrumb({ level, date, first, last, onDateChange }: MapBreadcrumbProps) {
  const { search } = useLocation()
  const trail = STEPS.filter((step) => step.level <= level)
  const above = trail.length > 1 ? trail[trail.length - 2] : null
  return (
    <div className="map-breadcrumb" data-level={level}>
      {above && (
        <Link to={MAP_PATHS[above.level] + levelSearch(above.level, search)} className="map-breadcrumb-back label-ui">
          <Icon name="chevron-left" size={16} />
          {above.level === 1 ? 'All cities' : above.name}
        </Link>
      )}
      <nav aria-label="Breadcrumb" className="map-breadcrumb-nav">
        <ol className="map-breadcrumb-trail label-ui">
          {trail.map((step) => (
            <li key={step.level}>
              {step.level > 1 && (
                <span className="map-breadcrumb-separator" aria-hidden="true">
                  ›
                </span>
              )}
              {step.level === level ? (
                // Figma greys the trail's only step at level 1 and darkens the open one below it
                <span aria-current="page" className={level > 1 ? 'map-breadcrumb-open' : undefined}>
                  {step.name}
                </span>
              ) : (
                <Link to={MAP_PATHS[step.level] + levelSearch(step.level, search)}>{step.name}</Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
      <div className="map-breadcrumb-date">
        <DatePicker value={date} min={first} max={last} onChange={onDateChange} />
      </div>
    </div>
  )
}
