import type { ReactNode } from 'react'
import { Link } from 'react-router'
import Icon, { type IconName } from './Icon.tsx'
import './Button.css'

type ButtonProps = {
  /** Primary (filled teal), Secondary (outlined) or Ghost (text only). */
  variant?: 'primary' | 'secondary' | 'ghost'
  /** An icon after the label, 18 px. Figma's buttons show 'arrow-right'. */
  icon?: IconName
  /** A route in the app, e.g. '/map': the button is a link to it. */
  to?: string
  /** An address on another site: the button is a link that opens it in a new tab. */
  href?: string
  /** What happens on click, for a button that is not a link. */
  onClick?: () => void
  /** Extra classes, e.g. to make the button full width in a panel. */
  className?: string
  /** The label. */
  children: ReactNode
}

/**
 * F3: the Figma component "Button" (node 3:65) in its three styles. With `to` it is a link to
 * a route, with `href` a link to another site, and otherwise a <button>.
 */
export default function Button({
  variant = 'primary',
  icon,
  to,
  href,
  onClick,
  className,
  children,
}: ButtonProps) {
  const classes = ['button', `button-${variant}`, 'label-ui', className].filter(Boolean).join(' ')
  const content = (
    <>
      {children}
      {icon && <Icon name={icon} size={18} />}
    </>
  )

  if (to) {
    return (
      <Link to={to} className={classes}>
        {content}
      </Link>
    )
  }
  if (href) {
    return (
      <a href={href} className={classes} target="_blank" rel="noreferrer">
        {content}
      </a>
    )
  }
  return (
    <button type="button" className={classes} onClick={onClick}>
      {content}
    </button>
  )
}
