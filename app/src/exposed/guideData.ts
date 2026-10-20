import { useEffect, useState } from 'react'
import { titleCase } from '../map/plan.ts'
import type { BarangayShapes, CentersFile } from '../map/planData.ts'
import { shapeMiddle, shapeParts, type LonLat } from './nearest.ts'

/**
 * F8: the two files the guide's last step reads, written by F2 (python -m src.app_data), and
 * what the guide keeps of them:
 *
 *   centers.json           the health centers' names, barangays and coordinates (A10's registry)
 *   qc_barangays.geojson   the 142 barangays' outlines: for the map, for the barangay the reader
 *                          is in, and for the barangay search
 *
 * They are fetched when the reader asks for the nearest health centers, and kept. They hold
 * nothing about the reader, so fetching them tells the server nothing either.
 */

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

/**
 * What the guide keeps of F2's two files. The health centers are the 66 that C7 sends stock to
 * (`left_out` empty), the plan's "66 health centers": the registry's second entry for Bago
 * Bantay Health Center has no coordinates (its first entry, with them, is listed), and Villamor
 * Barangay Health Station's point lies 11 km from the barangay it is registered in, so the guide
 * sends nobody there. Stops with an error if a listed center has no coordinates.
 */
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

/**
 * Fetches one of F2's files and reads its JSON; a missing file (404) stops with an error. The
 * same as fetchJson in map/mapData.ts, which the router loads only with the map: imported here,
 * it would come along with every page (Vite warns of that).
 */
async function fetchFile<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`${path}: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

let guideFiles: Promise<GuideData> | null = null

/**
 * The guide's files, fetched together the first time the reader asks for the nearest health
 * centers, and kept for the next time. A failed fetch is tried again then.
 */
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
