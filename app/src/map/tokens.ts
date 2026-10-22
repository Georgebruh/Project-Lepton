/**
 * F13: a color token's value from tokens.css ('map-land' reads --color-map-land), as the map's
 * element sees it. MapLibre draws on a canvas and cannot read CSS variables, so the map's layers
 * read each token once, when they are added.
 */
export function tokenColor(element: HTMLElement, token: string): string {
  return getComputedStyle(element).getPropertyValue(`--color-${token}`).trim()
}
