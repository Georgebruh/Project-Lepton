import type { ReactNode } from 'react'
import './Badge.css'

type BadgeProps = {
  /**
   * The color, by meaning (Design notes): accent = teal, for action and exposure; warn =
   * amber, for warnings and simulated data; alert = red, for alerts only; neutral = grey.
   */
  tone?: 'neutral' | 'accent' | 'warn' | 'alert'
  /** Extra classes, e.g. to place the badge in a layout. */
  className?: string
  /** The label, e.g. "Simulated until QCESD data". */
  children: ReactNode
}

/** F3: the Figma component "Badge" (node 3:78): a small square dot and a short label. */
export default function Badge({ tone = 'neutral', className, children }: BadgeProps) {
  const classes = ['badge', `badge-${tone}`, 'label-eyebrow', className].filter(Boolean).join(' ')
  return (
    <span className={classes}>
      <span className="badge-dot" aria-hidden="true" />
      {children}
    </span>
  )
}
