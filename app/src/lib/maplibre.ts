/**
 * F1: MapLibre GL JS, set up for Vite. Map code imports it from here, never from
 * 'maplibre-gl' directly:
 *
 *   import maplibregl from '../lib/maplibre.ts'
 *   const map = new maplibregl.Map({ container, style })
 *
 * MapLibre prepares GeoJSON and tiles in a web worker, a second script it loads from a file
 * next to its own code. Vite bundles MapLibre's code but not that file, so without the
 * setWorkerUrl line below every GeoJSON layer fails with "Worker failed to load". The ?url
 * import makes Vite copy the worker file into the build and gives its address.
 * This file also loads MapLibre's stylesheet (its controls, popups and attribution).
 */
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

maplibregl.setWorkerUrl(workerUrl)

export default maplibregl
