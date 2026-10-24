import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'

/* When a map source has drawn, for the layers fetched while the reader waits. */

/** Whether an error MapLibre raised came from the source `id` (it adds the id to its sources' errors). */
export function isSourceError(event: MapEventType['error'], id: string): boolean {
  return 'sourceId' in event && event.sourceId === id
}

/** Calls `onReady` once the source `id` has its tiles where the map is now. */
export function whenSourceReady(map: MapLibreMap, id: string, onReady: () => void, onError: () => void): () => void {
  const check = () => {
    if (map.getSource(id) && map.isSourceLoaded(id)) {
      stop()
      onReady()
    }
  }
  const onData = (event: MapEventType['sourcedata']) => {
    if (event.sourceId === id && event.tile) {
      check()
    }
  }
  const onFail = (event: MapEventType['error']) => {
    if (isSourceError(event, id)) {
      stop()
      onError()
    }
  }
  function stop() {
    map.off('sourcedata', onData)
    map.off('render', check)
    map.off('error', onFail)
  }
  map.on('sourcedata', onData)
  map.on('render', check)
  map.on('error', onFail)
  map.triggerRepaint() // Draw a frame even if nothing else moves, so the check runs
  return stop
}
