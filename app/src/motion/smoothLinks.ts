import { useEffect } from 'react'
import { prefersReducedMotion } from '../map/motion.ts'

/** A click on a link to a place on the same page glides there; every other scroll stays instant. */
export function useSmoothInPageLinks() {
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const link = event.target instanceof Element ? event.target.closest('a[href^="#"]') : null
      if (!link || prefersReducedMotion()) {
        return
      }
      const root = document.documentElement
      root.style.scrollBehavior = 'smooth'
      // The glide starts with the click; from the next frame, scrolling is instant again
      requestAnimationFrame(() => root.style.removeProperty('scroll-behavior'))
    }
    document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [])
}
