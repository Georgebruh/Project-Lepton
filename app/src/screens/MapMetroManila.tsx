import ForecastPanel from '../map/ForecastPanel.tsx'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import { QC_PSGC } from '../map/routes.ts'

/**
 * Map, level 1: Metro Manila (route /map). Task F4 builds it from the Figma frames
 * "1 Metro Manila" (node 55:318) and its hovers "1a" (55:473) and "1b" (55:628); the map, its
 * names, legend and tooltips are MapLayout's. This route fills the panel, which waits
 * off-screen at this level with Quezon City's forecast, as in Figma frame 1, so that it slides
 * in already filled when the city is clicked. Reads /data/ncr_cities.geojson and
 * /data/city_forecast.json, written by F2.
 */
export default function MapMetroManila() {
  const { cities, forecast, week } = useMapContext()
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties
  return (
    <>
      <title>Metro Manila · LEPTON</title>
      <ForecastPanel city={shortName(qc)} forecast={forecast} week={week} />
    </>
  )
}
