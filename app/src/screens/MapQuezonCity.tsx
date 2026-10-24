import ForecastPanel from '../map/ForecastPanel.tsx'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import { QC_PSGC } from '../map/routes.ts'

/** Map, level 2: Quezon City's case forecast (route /map/quezon-city). */
export default function MapQuezonCity() {
  const { cities, forecast, week } = useMapContext()
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties
  return (
    <>
      <ForecastPanel city={shortName(qc)} forecast={forecast} week={week} />
    </>
  )
}
