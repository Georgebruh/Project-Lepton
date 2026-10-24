import { useLayoutEffect, useRef } from 'react'

/** Things that arrive together in one list start one after another, at most this many steps late. */
const MAX_ORDER = 6

/** Content counts as in view once it is above the screen's bottom 8%. */
const IN_VIEW = '0px 0px -8% 0px'

/** Shows each [data-reveal] element inside the returned ref's element the first time it scrolls into view. */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  // Before the first paint, so nothing shows and then hides
  useLayoutEffect(() => {
    const root = ref.current
    if (!root) {
      return
    }
    root.setAttribute('data-reveal-root', '')
    const observer = new IntersectionObserver(
      (entries) => {
        // Numbered within each parent: a list's items arriving together
        const counts = new Map<Element | null, number>()
        for (const entry of entries) {
          if (!entry.isIntersecting) {
            continue
          }
          const element = entry.target as HTMLElement
          const order = counts.get(element.parentElement) ?? 0
          counts.set(element.parentElement, order + 1)
          element.style.setProperty('--reveal-order', String(Math.min(order, MAX_ORDER)))
          element.setAttribute('data-revealed', '')
          observer.unobserve(element)
        }
      },
      { rootMargin: IN_VIEW },
    )
    // Also the elements added later, as a file loads
    const watch = () => {
      root.querySelectorAll('[data-reveal]:not([data-revealed])').forEach((element) => observer.observe(element))
    }
    watch()
    const added = new MutationObserver(watch)
    added.observe(root, { childList: true, subtree: true })
    return () => {
      observer.disconnect()
      added.disconnect()
      root.removeAttribute('data-reveal-root')
    }
  }, [])
  return ref
}
