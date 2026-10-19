import { useMatches } from 'react-router'

/**
 * F4: the map's three levels and their addresses. Each map route in router.tsx names its
 * level in its handle ({ mapLevel: 2 }), so the layout knows which level is open.
 */
export type MapLevel = 1 | 2 | 3

/** Each level's address: Metro Manila, Quezon City's case forecast, its prophylaxis plan (F5). */
export const MAP_PATHS: Record<MapLevel, string> = {
  1: '/map',
  2: '/map/quezon-city',
  3: '/map/quezon-city/prophylaxis',
}

/** Quezon City's 10-digit PSGC (config.QC_CITY_PSGC): the only city with weekly case counts. */
export const QC_PSGC = '1381300000'

/** The address of each city whose forecast can be opened, by PSGC: Quezon City only, so far. */
export const CITY_PATHS: Record<string, string> = { [QC_PSGC]: MAP_PATHS[2] }

/**
 * F5: the prophylaxis plan's own settings in the address: the forecast's lead time
 * (?lead=2), the storm list shown even on a date with a storm (?storms=all), and the date the
 * reader had before opening a storm from that list (?from=2026-10-03), to go back to.
 */
export const PLAN_PARAMS = { lead: 'lead', list: 'storms', from: 'from' }

/**
 * The query a link to a map level carries: the address's own, so the date stays. A link out
 * of the prophylaxis plan, though, leaves the plan's settings behind and puts back the date
 * the reader had before opening a storm from its list: a storm opened there is a visit, and
 * the plan opens afresh next time (F5).
 */
export function levelSearch(level: MapLevel, search: string): string {
  if (level === 3) {
    return search
  }
  const params = new URLSearchParams(search)
  const from = params.get(PLAN_PARAMS.from)
  if (from) {
    params.set('date', from)
  }
  for (const name of Object.values(PLAN_PARAMS)) {
    params.delete(name)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

/** The map level the open route names in its handle; 1 (Metro Manila) if none does. */
export function useMapLevel(): MapLevel {
  const matches = useMatches()
  for (const match of [...matches].reverse()) {
    const level = (match.handle as { mapLevel?: MapLevel } | undefined)?.mapLevel
    if (level) {
      return level
    }
  }
  return 1
}
