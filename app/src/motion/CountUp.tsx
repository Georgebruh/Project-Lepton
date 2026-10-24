import { useEffect, useRef, useState } from 'react'
import { prefersReducedMotion } from '../map/motion.ts'

/** How long a number takes to count up, ms. */
const COUNT_MS = 1200

type CountUpProps = {
  /** The number it ends at. */
  value: number
  /** Writes a number as the page does, e.g. formatCount. */
  format: (n: number) => string
}

/** A number that counts up from 0 the first time it scrolls into view; screen readers hear only `value`. */
export default function CountUp({ value, format }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null)
  // The number shown while counting; null before and after, when `value` shows
  const [shown, setShown] = useState<number | null>(null)
  useEffect(() => {
    const element = ref.current
    if (!element || prefersReducedMotion()) {
      return
    }
    let frame = 0
    // From its first pixel in view, so the final number never shows before the count
    const observer = new IntersectionObserver((entries) => {
      if (!entries[entries.length - 1].isIntersecting) {
        return
      }
      observer.disconnect()
      setShown(0)
      const start = performance.now()
      const step = (now: number) => {
        // A frame's time can be a little before `start`
        const t = Math.min(1, Math.max(0, (now - start) / COUNT_MS))
        setShown(t < 1 ? Math.round(value * easeOut(t)) : null)
        if (t < 1) {
          frame = requestAnimationFrame(step)
        }
      }
      frame = requestAnimationFrame(step)
    })
    observer.observe(element)
    return () => {
      observer.disconnect()
      cancelAnimationFrame(frame)
    }
  }, [value])
  const counting = shown !== null
  return (
    <span ref={ref}>
      <span aria-hidden={counting || undefined}>{format(shown ?? value)}</span>
      {counting && <span className="visually-hidden">{format(value)}</span>}
    </span>
  )
}

/** Fast, then slow: t from 0 to 1 becomes the share of the count done. */
function easeOut(t: number): number {
  return 1 - (1 - t) ** 3
}
