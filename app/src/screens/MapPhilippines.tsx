import ForecastPanel from '../map/ForecastPanel.tsx'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import { QC_PSGC } from '../map/routes.ts'

/**
 * Map, level 1: the Philippines (route /map). Task F4 built it as Metro Manila from the Figma
 * frames "1 Metro Manila" (node 55:318) and its hovers "1a" (55:473) and "1b" (55:628); F14
 * widened it to every city and municipality of the country. The map, its legend and tooltips
 * are MapLayout's. This route fills the panel, which waits off-screen at this level with Quezon
 * City's forecast, as in Figma frame 1, so that it slides in already filled when the city is
 * clicked. Reads /data/ph_cities.json and /data/city_forecast.json, written by F2.
 */
export default function MapPhilippines() {
  const { cities, forecast, week } = useMapContext()
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties
  return (
    <>
      <title>Leptospirosis map of the Philippines · LEPTON</title>
      <ForecastPanel city={shortName(qc)} forecast={forecast} week={week} />
    </>
  )
}
