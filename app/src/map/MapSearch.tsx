import { useEffect, useId, useMemo, useRef, useState, type FocusEvent, type KeyboardEvent } from 'react'
import Icon from '../components/Icon.tsx'
import { matchPlaces } from '../exposed/nearest.ts'
import { shortName, type Cities } from './mapData.ts'
import { CITY_PATHS } from './routes.ts'
import './MapSearch.css'

/** How many matching places the list shows at once. */
const SHOWN_MATCHES = 8

/** A place the search finds: a city or municipality, by the name the map writes ("Marikina"). */
type Place = { psgc: string; name: string; province: string; hasData: boolean }

type MapSearchProps = {
  cities: Cities
  /** Called with the PSGC of the place the reader picks. */
  onPick: (psgc: string) => void
}

/** The map's search, beside the logo in the top left corner. */
export default function MapSearch({ cities, onPick }: MapSearchProps) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const [active, setActive] = useState(0)
  const button = useRef<HTMLButtonElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const refocus = useRef(false) // Give the keyboard back to the button once the field has closed
  const places = useMemo<Place[]>(
    () =>
      cities.features.map(({ properties: city }) => ({
        psgc: city.psgc,
        name: shortName(city),
        province: city.province,
        hasData: city.psgc in CITY_PATHS,
      })),
    [cities],
  )
  const matches = matchPlaces(places, typed, places.length)
  const shown = matches.slice(0, SHOWN_MATCHES)
  const searching = typed.trim() !== ''

  // The field takes the keyboard as it opens; once it closes, the button takes it back
  useEffect(() => {
    if (open) {
      input.current?.focus()
    } else if (refocus.current) {
      refocus.current = false
      button.current?.focus()
    }
  }, [open])

  /** Closes the field and forgets what was typed; `toButton` gives the keyboard back to the button. */
  function close(toButton: boolean) {
    refocus.current = toButton
    setOpen(false)
    setTyped('')
    setActive(0)
  }

  function pick(place: Place) {
    close(!place.hasData) // A city with data opens its panel, which takes the keyboard (MapLayout)
    onPick(place.psgc)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' && shown.length > 0) {
      event.preventDefault()
      setActive((index) => Math.min(index + 1, shown.length - 1))
    } else if (event.key === 'ArrowUp' && shown.length > 0) {
      event.preventDefault()
      setActive((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && shown.length > 0) {
      event.preventDefault()
      pick(shown[active])
    } else if (event.key === 'Escape') {
      event.preventDefault()
      close(true)
    }
  }

  /** Leaving the search (a click on the map, Tab past the close button) closes it. */
  function onBlur(event: FocusEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      close(false)
    }
  }

  if (!open) {
    return (
      <button
        ref={button}
        type="button"
        className="map-search-button"
        aria-label="Search for a city or municipality"
        title="Search for a city or municipality"
        onClick={() => setOpen(true)}
      >
        <Icon name="search" size={18} />
      </button>
    )
  }

  // What the search found, for screen readers.
  let count = ''
  if (searching) {
    if (matches.length === 0) {
      count = `No city or municipality matches “${typed.trim()}”. Check the spelling.`
    } else if (matches.length > shown.length) {
      count = `${matches.length} places match; the first ${shown.length} are shown. Type more of the name.`
    } else {
      count = matches.length === 1 ? '1 place matches.' : `${matches.length} places match.`
    }
  }
  const countShown = searching && (matches.length === 0 || matches.length > shown.length)
  return (
    <div className="map-search" role="search" onBlur={onBlur}>
      <div className="map-search-field">
        <Icon name="search" size={18} className="map-search-icon" />
        <label htmlFor={`${id}-input`} className="visually-hidden">
          City or municipality
        </label>
        <input
          ref={input}
          id={`${id}-input`}
          className="map-search-input body-m"
          type="text"
          role="combobox"
          placeholder="Search a city or municipality"
          value={typed}
          onChange={(event) => {
            setTyped(event.target.value)
            setActive(0)
          }}
          onKeyDown={onKeyDown}
          autoComplete="off"
          autoCapitalize="words"
          spellCheck={false}
          enterKeyHint="search"
          aria-expanded={shown.length > 0}
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          aria-activedescendant={shown.length > 0 ? `${id}-option-${active}` : undefined}
          aria-describedby={`${id}-count`}
        />
        <button type="button" className="map-search-close" aria-label="Close the search" onClick={() => close(true)}>
          <Icon name="close" size={16} />
        </button>
      </div>
      {/* Under the field, over the map: the matches, then the count when it is shown. */}
      <div className="map-search-results">
        <ul id={`${id}-list`} className="map-search-list" role="listbox" aria-label="Cities and municipalities">
          {shown.map((place, index) => (
            <li
              key={place.psgc}
              id={`${id}-option-${index}`}
              className="map-search-option"
              role="option"
              aria-selected={index === active}
              onMouseDown={(event) => event.preventDefault()}
              onMouseMove={() => setActive(index)}
              onClick={() => pick(place)}
            >
              <span className="label-ui">{place.name}</span>
              <span className="map-search-province body-s">
                {place.province}
                {place.hasData && ' · has a forecast'}
              </span>
            </li>
          ))}
        </ul>
        <p
          id={`${id}-count`}
          className={countShown ? 'map-search-count body-s' : 'visually-hidden'}
          aria-live="polite"
        >
          {count}
        </p>
      </div>
    </div>
  )
}
