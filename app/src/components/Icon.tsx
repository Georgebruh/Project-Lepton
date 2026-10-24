import { ICON_SHAPES, type IconName } from './iconShapes.tsx'
import './Icon.css'

export type { IconName }

type IconProps = {
  /** Which icon, e.g. 'arrow-right'. */
  name: IconName
  /** Width and height in px. The design uses 24, 18 (in buttons) and 16 (beside text). */
  size?: number
  className?: string
}

/** One of the 23 icons, `size` px square, in the current text color. */
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
