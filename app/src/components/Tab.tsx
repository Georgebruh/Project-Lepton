import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import './Tab.css'

type TabProps = {
  /** A route, e.g. '/map': the tab is a link, selected while that route or one under it is open. */
  to?: string
  /** With `to`: select the tab only on that exact route, not the routes under it. */
  end?: boolean
  /**
   * Whether the tab is selected. With `to`, leave it out to select the tab on its route; F4's
   * map panel sets it, so its tab stays selected while the panel slides away after Back.
   */
  /** Without `to`: whether the tab is selected. */
  selected?: boolean
  /** Without `to`: what happens on click. */
  onClick?: () => void
  /** The label. */
  children: ReactNode
}

/**
 * F3: the Figma component "Tab" (node 3:83), Default or Selected. With `to` it is a link to a
 * route (the app bar's views, the panel's Cases and Prophylaxis); otherwise a button that
 * reports its state to screen readers with aria-pressed.
 */
export default function Tab({ to, end, selected = false, onClick, children }: TabProps) {
  if (to) {
    return (
      <NavLink
        to={to}
        end={end}
        className={({ isActive }) => (isActive ? 'tab tab-selected label-ui' : 'tab label-ui')}
      >
        {children}
      </NavLink>
    )
  }
  return (
    <button
      type="button"
      className={selected ? 'tab tab-selected label-ui' : 'tab label-ui'}
      aria-pressed={selected}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
