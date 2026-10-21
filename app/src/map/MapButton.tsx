import type { Ref } from 'react'
import Icon, { type IconName } from '../components/Icon.tsx'
import './MapButton.css'

type MapButtonProps = {
  icon: IconName
  /** What the button does: read out by screen readers and shown as its tooltip. */
  label: string
  onClick: () => void
  /** For a button that opens a panel (the Layers button): whether the panel is open, Figma's Open state. */
  open?: boolean
  /** The id of the panel the button opens, named only while it is open (the panel is in the page only then). */
  controls?: string
  /** The button element, for the layout to give the keyboard back to it when its panel closes. */
  ref?: Ref<HTMLButtonElement>
}

/**
 * F13: a map control above the Zoom buttons, Figma "Map button" (Components page): a 36 px
 * square, as wide as the Zoom box. The pin brings the open level back into view; the Layers
 * button opens the Layers panel and shows Figma's Open state while it is open.
 */
export default function MapButton({ icon, label, onClick, open, controls, ref }: MapButtonProps) {
  return (
    <button
      ref={ref}
      type="button"
      className={open ? 'map-button map-button-open' : 'map-button'}
      aria-label={label}
      title={label}
      aria-expanded={open}
      aria-controls={open ? controls : undefined}
      onClick={onClick}
    >
      <Icon name={icon} size={18} />
    </button>
  )
}
