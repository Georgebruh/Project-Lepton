import PanelModes from '../map/PanelModes.tsx'
import './MapProphylaxis.css'

/**
 * Map, level 3: the prophylaxis plan (route /map/quezon-city/prophylaxis). Task F5 builds it
 * from the Figma frames "3 Prophylaxis plan" (node 56:395) and its hover "3a" (57:741).
 * Reads /data/qc_barangays.geojson, /data/storms.json, the run's file in /data/barangays/
 * and /data/centers.json, written by F2.
 *
 * Until then it fills the map's panel with the panel's modes and a note (F4 put the map
 * levels' content in that panel). F5's parts: useMapContext() from map/mapContext.ts gives
 * the map, to add the barangay layers to, and the chosen date.
 */
export default function MapProphylaxis() {
  return (
    <div className="map-prophylaxis">
      <title>Prophylaxis plan · LEPTON</title>
      <PanelModes mode="prophylaxis" />
      <p className="map-prophylaxis-note label-eyebrow">Placeholder · built in F5</p>
      <h2 className="heading-l">Prophylaxis plan</h2>
    </div>
  )
}
