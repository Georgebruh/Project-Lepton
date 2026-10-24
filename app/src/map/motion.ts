/** The map's motion. */

/** A city under the pointer: its outline thickens and its tooltip fades in. */
export const HOVER_MS = 150

/** Opening or leaving a city: the camera move, the fade of the other cities, the panel slide. */
export const CAMERA_MS = 700

/** With reduced motion, every change is a crossfade of this length. */
export const CROSSFADE_MS = 150

/** The other cities' opacity while one city is open. */
export const DIMMED_OPACITY = 0.45

/** The city panel is a card on the left of the map, under the logo: 30% of the width, 432 px on a 1440 px screen. */
export const PANEL_SHARE = 0.3
export const PANEL_MIN_WIDTH = 400
export const PANEL_MAX_WIDTH = 480

/** The card's gap to the map's edges (MapLayout.css's --map-edge), and its tabs' width past its right edge. */
export const PANEL_INSET = 24
export const EDGE_TAB_WIDTH = 48

/** The panel's width in px beside a map `width` px wide (never wider than the map). */
export function panelWidth(width: number): number {
  return Math.min(width, Math.max(PANEL_MIN_WIDTH, Math.min(PANEL_MAX_WIDTH, Math.round(width * PANEL_SHARE))))
}

/** Below this width in px the panel is a sheet over the map's lower part. */
export const SHEET_BELOW = 600
export const SHEET_SHARE = 0.55

/** How much of a map `width` by `height` px the open panel covers, in px: the card, its gap and its tabs. */
export function panelCover(width: number, height: number): { left: number; bottom: number } {
  return width < SHEET_BELOW
    ? { left: 0, bottom: Math.round(height * SHEET_SHARE) }
    : { left: PANEL_INSET + panelWidth(width) + EDGE_TAB_WIDTH, bottom: 0 }
}

/** Opening the prophylaxis plan. */
export const LINES_MS = 300
export const WAVE_MS = 600

/** How long one barangay's fill takes to rise within the wave. */
export const RISE_MS = 150

/** The ease-in-out curve as CSS writes it: slow, fast, slow (easing "easeInOutCubic"). */
export const EASE_CSS = 'cubic-bezier(0.65, 0, 0.35, 1)'

/** The same curve for MapLibre's camera: t from 0 to 1 becomes the share of the way travelled. */
export function easeInOut(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
}

/** Whether the reader has asked their system for less motion. */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
