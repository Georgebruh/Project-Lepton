import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'

/*
 * F13: when a map source has drawn, for the layers fetched while the reader waits (NOAH's flood
 * zones, floodLayer.ts; each weather frame, weather.ts).
 */

/** Whether an error MapLibre raised came from the source `id` (it adds the id to its sources' errors). */
export function isSourceError(event: MapEventType['error'], id: string): boolean {
  return 'sourceId' in event && event.sourceId === id
}

/**
 * Calls `onReady` once the source `id` has its tiles where the map is now, or `onError` if the
 * source raises an error first; the returned function stops watching. "Ready" is checked as each
 * of its tiles arrives and after each frame the map draws, until it is ready: MapLibre asks for
 * the tiles it needs as it draws, so before that a source with no tiles asked for would look
 * loaded; and a source shown again takes its tiles back from MapLibre's cache with no tile event,
 * so one check after the next frame can miss them. (A tile the server does not have, a 404,
 * counts as arrived: MapLibre draws it as nothing.)
 */
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
  map.triggerRepaint() // draw a frame even if nothing else moves, so the check runs
  return stop
}
