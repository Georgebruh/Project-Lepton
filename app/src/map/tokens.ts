/** A color token's value from tokens.css. */
export function tokenColor(element: HTMLElement, token: string): string {
  return getComputedStyle(element).getPropertyValue(`--color-${token}`).trim()
}
