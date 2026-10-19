import { NavLink } from 'react-router'
import './Placeholder.css'

/** The eight screens' routes and names, for the list on every placeholder (as in router.tsx). */
const SCREENS = [
  { path: '/', name: 'Home' },
  { path: '/map', name: 'Map: Metro Manila' },
  { path: '/map/quezon-city', name: "Map: Quezon City's case forecast" },
  { path: '/map/quezon-city/prophylaxis', name: 'Map: prophylaxis plan' },
  { path: '/leptospirosis', name: 'Leptospirosis' },
  { path: '/exposed', name: 'Exposure guide' },
  { path: '/compare', name: 'Compare models' },
  { path: '/how-it-works', name: 'How it works' },
]

type PlaceholderProps = {
  /** The screen's name, as in the plan's Screens table. */
  screen: string
  /** The task that builds the screen, e.g. 'F4'. */
  task: string
}

/**
 * F1: the stand-in for a screen that is not built yet. It shows the screen's name, the task
 * that builds it and links to all eight screens. Each screen's task replaces it; delete this
 * file and Placeholder.css when no screen uses it.
 */
export default function Placeholder({ screen, task }: PlaceholderProps) {
  return (
    <main className="placeholder">
      <p className="label-eyebrow placeholder-task">Placeholder · built in {task}</p>
      <h1 className="heading-l">{screen}</h1>
      <nav aria-label="All screens">
        <ul className="placeholder-screens">
          {SCREENS.map(({ path, name }) => (
            <li key={path}>
              <NavLink to={path} end className="label-ui">
                {name}
              </NavLink>
              <span className="data-m">{path}</span>
            </li>
          ))}
        </ul>
      </nav>
    </main>
  )
}
