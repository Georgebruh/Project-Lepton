import { useEffect, type RefObject } from 'react'

/** While `open`, calls `onClose` when the pointer presses anywhere outside `box` (a pop-up and its button). */
export function useOutsidePress(open: boolean, box: RefObject<HTMLElement | null>, onClose: () => void) {
  useEffect(() => {
    if (!open) {
      return
    }
    function onPress(event: PointerEvent) {
      if (!box.current?.contains(event.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('pointerdown', onPress)
    return () => document.removeEventListener('pointerdown', onPress)
  }, [open, box, onClose])
}
