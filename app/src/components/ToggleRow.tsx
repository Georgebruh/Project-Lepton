import type { CSSProperties } from 'react'
import './ToggleRow.css'

type ToggleRowProps = {
  /** The label, e.g. a model's name. */
  label: string
  /** Whether the toggle is on. */
  on: boolean
  /** Called with the new state when the row is clicked. */
  onChange: (on: boolean) => void
  /**
   * The swatch's color while on, as a token: 'var(--color-chart-m3)'. Teal
   * (--color-accent-primary) when left out. Compare models (F9) passes each model's color.
   */
  color?: string
}

/**
 * F3: the Figma component "Toggle row" (node 3:94), On or Off: a color swatch, a label and a
 * switch. The whole row is one switch (role="switch"), so a click anywhere on it, or Space or
 * Enter, flips it.
 */
export default function ToggleRow({ label, on, onChange, color }: ToggleRowProps) {
  const style = color ? ({ '--toggle-row-color': color } as CSSProperties) : undefined
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      className={on ? 'toggle-row toggle-row-on' : 'toggle-row'}
      style={style}
      onClick={() => onChange(!on)}
    >
      <span className="toggle-row-swatch" aria-hidden="true" />
      <span className="toggle-row-label body-m">{label}</span>
      <span className="toggle-row-switch" aria-hidden="true">
        <span className="toggle-row-knob" />
      </span>
    </button>
  )
}
