import { ICON_SHAPES, type IconName } from './iconShapes.tsx'
import './Icon.css'

export type { IconName }

type IconProps = {
  /** Which icon, e.g. 'arrow-right'. */
  name: IconName
  /** Width and height in px. Figma uses 24, 18 (in buttons) and 16 (beside text). */
  size?: number
  className?: string
}

/**
 * F3: one of the 20 icons from the Figma Components page (F14's search is not in Figma), `size` px square, in the current
 * text color. Lines keep their Figma width (1.5, 1.75 or 2 px) at every size, as they do when
 * an icon is resized in Figma (Icon.css). The icon is decoration, hidden from screen readers:
 * the button or link around it carries the words.
 */
export default function Icon({ name, size = 24, className }: IconProps) {
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {ICON_SHAPES[name]}
    </svg>
  )
}
