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
   * The series' color, as a token: 'var(--color-chart-m3)'. The swatch keeps it on and off, as
   * in Figma's Compare models frame (F9 passes each model's color), so it names the series like
   * a key. Without it the swatch is teal when on and grey when off (the component's variants).
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
  const classes = ['toggle-row', on && 'toggle-row-on', color && 'toggle-row-colored'].filter(Boolean).join(' ')
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      className={classes}
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
