import ForecastPanel from '../map/ForecastPanel.tsx'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import { QC_PSGC } from '../map/routes.ts'

/**
 * Map, level 2: Quezon City's case forecast (route /map/quezon-city). Task F4 builds it from
 * the Figma frame "2 Quezon City" (node 53:268): the camera fits the city beside the panel,
 * which shows next week's forecast for the chosen date (map/ForecastPanel.tsx). Reads
 * /data/city_forecast.json, written by F2.
 */
export default function MapQuezonCity() {
  const { cities, forecast, week } = useMapContext()
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties
  return (
    <>
      <title>Quezon City · LEPTON</title>
      <ForecastPanel city={shortName(qc)} forecast={forecast} week={week} />
    </>
  )
}
