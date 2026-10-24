import { useEffect, useState } from 'react'
import { titleCase } from '../map/plan.ts'
import type { BarangayShapes, CentersFile } from '../map/planData.ts'
import { shapeMiddle, shapeParts, type LonLat } from './nearest.ts'

/** The two files the guide's last step reads. */

/** A health center the guide can send a reader to. */
export type GuideCenter = {
  facilityCode: string
  /** Its name in title case: "Tatalon Health Center". */
  name: string
  /** The barangay it is in. */
  barangay: string
  lon: number
  lat: number
}

/** A barangay, as the guide uses it. */
export type GuideBarangay = {
  /** The 10-digit PSGC, e.g. "1381300121". */
  psgc: string
  name: string
  /** Every ring of its outline (outer rings and any holes): is a point inside it, and the map. */
  rings: LonLat[][]
  /** A point inside it, near its middle: where the distances start when the reader picks it. */
  middle: LonLat
}

export type GuideData = { centers: GuideCenter[]; barangays: GuideBarangay[] }

/** What the guide keeps of the two files. */
export function guideData(centers: CentersFile, shapes: BarangayShapes): GuideData {
  const listed = centers.centers.filter((center) => center.left_out === null)
  const guideCenters = listed.map((center) => {
    if (center.lat === null || center.lon === null) {
      throw new Error(`centers.json: ${center.name} has no coordinates: rerun python -m src.app_data`)
    }
    return {
      facilityCode: center.facility_code,
      name: titleCase(center.name),
      barangay: center.barangay,
      lon: center.lon,
      lat: center.lat,
    }
  })
  const barangays = shapes.features.map(({ properties, geometry }) => {
    const polygons = shapeParts(geometry)
    // A barangay in several parts starts its distances from its largest part
    return { psgc: properties.psgc, name: properties.name, rings: polygons.flat(), middle: shapeMiddle(polygons) }
  })
  return { centers: guideCenters, barangays }
}

/** Fetches one of the files and reads its JSON; a missing file (404) stops with an error. */
async function fetchFile<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`${path}: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

let guideFiles: Promise<GuideData> | null = null

/** The guide's files, fetched together the first time the reader asks for the nearest health centers. */
export function loadGuideData(): Promise<GuideData> {
  if (!guideFiles) {
    guideFiles = Promise.all([
      fetchFile<CentersFile>('/data/centers.json'),
      fetchFile<BarangayShapes>('/data/qc_barangays.geojson'),
    ]).then(([centers, shapes]) => guideData(centers, shapes))
    guideFiles.catch((error: unknown) => {
      console.error(error)
      guideFiles = null
    })
  }
  return guideFiles
}

/** The guide's files for a component: `data` once loaded, `failed` if they could not load, and `retry`. */
export function useGuideData(): { data?: GuideData; failed: boolean; retry: () => void } {
  const [loaded, setLoaded] = useState<{ data?: GuideData; failed: boolean }>({ failed: false })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let current = true
    loadGuideData().then(
      (data) => {
        if (current) {
          setLoaded({ data, failed: false })
        }
      },
      () => {
        if (current) {
          setLoaded({ failed: true })
        }
      },
    )
    return () => {
      current = false
    }
  }, [attempt])
  return {
    ...loaded,
    retry: () => {
      setLoaded({ failed: false })
      setAttempt((count) => count + 1)
    },
  }
}
