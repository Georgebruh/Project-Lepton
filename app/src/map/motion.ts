/**
 * F4: the map's motion, from the Figma notes "Map drill-down · design notes" (node 58:447):
 * hover 150 ms; clicking a city fits the camera to it in 700 ms (ease-in-out) while the other
 * cities fade to 45% and the panel slides in from the right; Back plays the same path in
 * reverse. With reduced motion: 150 ms crossfades and no camera move.
 *
 * MapLayout hands these numbers to its CSS as variables (--map-hover-ms and the rest), so the
 * CSS transitions and MapLibre's camera always use the same durations and curve.
 */

/** A city under the pointer: its outline thickens and its tooltip fades in. */
export const HOVER_MS = 150

/** Opening or leaving a city: the camera move, the fade of the other cities, the panel slide. */
export const CAMERA_MS = 700

/** With reduced motion, every change is a crossfade of this length. */
export const CROSSFADE_MS = 150

/** The other cities' opacity while one city is open. */
export const DIMMED_OPACITY = 0.45

/** The side panel's width in px (Figma frame 2); the camera keeps the open city clear of it. */
export const PANEL_WIDTH = 400

/**
 * F11: below this width in px the panel is a sheet that slides up over the map's lower part
 * instead of a column beside it (MapLayout.css's media query uses the same number), and the
 * share of the map's height the sheet covers. Figma has no phone frame for the map.
 */
export const SHEET_BELOW = 600
export const SHEET_SHARE = 0.55

/**
 * How much of a map `width` by `height` px the open panel covers, in px: its right side when
 * the panel sits beside it, or its lower part when the panel is a sheet (F11). The camera keeps
 * the open city clear of it, and the tooltips stay out from under it.
 */
export function panelCover(width: number, height: number): { right: number; bottom: number } {
  return width < SHEET_BELOW ? { right: 0, bottom: Math.round(height * SHEET_SHARE) } : { right: PANEL_WIDTH, bottom: 0 }
}

/**
 * F5, opening the prophylaxis plan: first the barangay lines fade in, in LINES_MS; then the
 * barangay fills rise in a wave from the most exposed barangay to the least, all within WAVE_MS,
 * while the city's own fill fades out. Back plays it in reverse.
 */
export const LINES_MS = 300
export const WAVE_MS = 600

/**
 * How long one barangay's fill takes to rise within the wave. The notes ask for starts "about
 * 20 ms apart" and "600 ms in all", but 142 starts 20 ms apart would take 2.8 s. So the 600 ms
 * wins: the starts are spread evenly over the first 450 ms (about 3 ms apart, a few barangays a
 * frame), and each fill rises in 150 ms.
 */
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
