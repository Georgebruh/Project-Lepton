import Placeholder from './Placeholder.tsx'

/**
 * Map, level 3: the prophylaxis plan (route /map/quezon-city/prophylaxis). Task F5 builds it
 * from the Figma frames "3 Prophylaxis plan" (node 56:395) and its hover "3a" (57:741).
 * Reads /data/qc_barangays.geojson, /data/storms.json, the run's file in /data/barangays/
 * and /data/centers.json, written by F2.
 */
export default function MapProphylaxis() {
  return <Placeholder screen="Map: prophylaxis plan" task="F5" />
}
