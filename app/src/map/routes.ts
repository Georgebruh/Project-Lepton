import { useMatches } from 'react-router'

/** The map's three levels and their addresses. */
export type MapLevel = 1 | 2 | 3

/** Each level's address: the Philippines, Quezon City's case forecast, its prophylaxis plan. */
export const MAP_PATHS: Record<MapLevel, string> = {
  1: '/map',
  2: '/map/quezon-city',
  3: '/map/quezon-city/prophylaxis',
}

/** Quezon City's 10-digit PSGC (config.QC_CITY_PSGC): the only city with weekly case counts. */
export const QC_PSGC = '1381300000'

/** The address of each city whose forecast can be opened, by PSGC: Quezon City only, so far. */
export const CITY_PATHS: Record<string, string> = { [QC_PSGC]: MAP_PATHS[2] }

/** The prophylaxis plan's own settings in the address: which forecast, by its lead time in days. */
export const PLAN_PARAMS = { lead: 'lead' }

/** The query a link to a map level carries: the address's own, so the date stays. */
export function levelSearch(level: MapLevel, search: string): string {
  if (level === 3) {
    return search
  }
  const params = new URLSearchParams(search)
  for (const name of Object.values(PLAN_PARAMS)) {
    params.delete(name)
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

/** The map level the open route names in its handle; 1 (the Philippines) if none does. */
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
