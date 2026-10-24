import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import './Tab.css'

type TabProps = {
  /** A route, e.g. '/map': the tab is a link, selected while that route or one under it is open. */
  to?: string
  /** With `to`: select the tab only on that exact route, not the routes under it. */
  end?: boolean
  /** Whether the tab is selected. */
  selected?: boolean
  /** A place on the same page, e.g. '#models': the tab is a plain link to it. */
  href?: string
  /** Without `to` or `href`: what happens on click. */
  onClick?: () => void
  /** The label. */
  children: ReactNode
}

/** The "Tab" component, Default or Selected. */
export default function Tab({ to, end, selected, href, onClick, children }: TabProps) {
  if (to) {
    return (
      <NavLink
        to={to}
        end={end}
        // NavLink marks the link as the current page whenever its route is open.
        aria-current={selected === false ? 'false' : 'page'}
        className={({ isActive }) => ((selected ?? isActive) ? 'tab tab-selected label-ui' : 'tab label-ui')}
      >
        {children}
      </NavLink>
    )
  }
  if (href) {
    return (
      <a
        href={href}
        aria-current={selected ? 'location' : undefined}
        className={selected ? 'tab tab-selected label-ui' : 'tab label-ui'}
      >
        {children}
      </a>
    )
  }
  return (
    <button
      type="button"
      className={selected ? 'tab tab-selected label-ui' : 'tab label-ui'}
      aria-pressed={selected ?? false}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
