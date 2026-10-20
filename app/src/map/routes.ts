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
