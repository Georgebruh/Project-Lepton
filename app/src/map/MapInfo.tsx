import type { Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useId, useRef, type KeyboardEvent } from 'react'
import { Link } from 'react-router'
import Icon from '../components/Icon.tsx'
import maplibregl from '../lib/maplibre.ts'
import MapButton from './MapButton.tsx'
import { useOutsidePress } from './useOutsidePress.ts'
import './MapInfo.css'

type MapInfoProps = {
  map: MapLibreMap | null
  /** The data mode's sentence (MapDataModes.tsx's dataNote). */
  note: string
  open: boolean
  onToggle: () => void
  /** Closes the pop-up; the same function every render, so a press outside is listened for once per opening. */
  onClose: () => void
}

/**
 * The info button at the bottom of the map buttons. Its pop-up holds what used to sit on the map: the link to
 * Methods (How it works), the data mode's sentence and the sources' credits.
 */
export default function MapInfo({ map, note, open, onToggle, onClose }: MapInfoProps) {
  const id = useId()
  const box = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const credits = useRef<HTMLDivElement>(null)
  useOutsidePress(open, box, onClose)

  // The credits are MapLibre's own attribution control, written out in full inside the pop-up
  useEffect(() => {
    const slot = credits.current
    if (!open || !map || !slot) {
      return
    }
    const control = new maplibregl.AttributionControl({ compact: false })
    slot.appendChild(control.onAdd(map))
    return () => control.onRemove()
  }, [open, map])

  /** Escape closes the pop-up and gives the keyboard back to its button. */
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      onClose()
      button.current?.focus()
    }
  }

  return (
    <div ref={box} className="map-info" onKeyDown={onKeyDown}>
      {open && (
        <section id={id} className="map-info-box" aria-label="About the map">
          <Link to="/how-it-works" className="map-info-methods label-ui">
            Methods
            <Icon name="arrow-right" size={16} />
          </Link>
          <div className="map-info-part">
            <p className="map-info-head label-ui-s">Data</p>
            <p className="body-s">{note}</p>
          </div>
          <div className="map-info-part">
            <p className="map-info-head label-ui-s">Map</p>
            <div ref={credits} className="map-info-credits body-s" />
          </div>
        </section>
      )}
      <MapButton ref={button} icon="info" label="About the map" open={open} controls={id} onClick={onToggle} />
    </div>
  )
}
