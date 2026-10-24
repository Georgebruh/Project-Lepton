import { useId, useImperativeHandle, useRef, useState, type KeyboardEvent, type ReactNode, type Ref } from 'react'
import './MapList.css'

/** One row of the list: a barangay. */
export type MapListItem = {
  /** Its PSGC. */
  id: string
  /** Its name, as the row and the search by typing read it. */
  name: string
  /** What the row shows before its name: the barangay's color on the map. */
  marker?: ReactNode
  /** What the row shows at its right end: the share of residents exposed. */
  detail?: ReactNode
  /** What a screen reader hears after the name. */
  words: string
  /** Whether Enter (or a click) opens it. */
  opens?: boolean
}

/** What a level can do with its list: move the keyboard to it (after its pop-up closes). */
export type MapListHandle = { focus: () => void }

type MapListProps = {
  /** What the rows are: "Barangays". */
  title: string
  items: MapListItem[]
  /** How the keyboard works here, read out with the list (not shown: the panel has no instructions). */
  instructions: string
  /** Shows a row's barangay on the map, as the pointer would; null when none is shown. */
  onShow: (id: string | null) => void
  /** Opens a row whose `opens` is true. */
  onOpen?: (id: string) => void
  ref?: Ref<MapListHandle>
}

/** A name as the search by typing compares it: lower case, without accents ("Doña" is "dona"). */
function plain(name: string): string {
  return name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** How long, in ms, keys typed one after another still add to the same search. */
const TYPING_MS = 700

/** The list of barangays in the plan's Barangays view: it reaches every barangay from the keyboard. */
export default function MapList({ title, items, instructions, onShow, onOpen, ref }: MapListProps) {
  const id = useId()
  const [activeId, setActiveId] = useState<string | null>(null)
  const listbox = useRef<HTMLUListElement>(null)
  const typed = useRef({ text: '', at: 0 })
  const active = items.find((item) => item.id === activeId) ?? items[0]

  useImperativeHandle(ref, () => ({
    focus() {
      listbox.current?.focus({ preventScroll: true })
    },
  }))

  /** Makes a row the active one, shows it on the map and scrolls it into the list's view. */
  function activate(item: MapListItem) {
    setActiveId(item.id)
    onShow(item.id)
    document.getElementById(`${id}-${item.id}`)?.scrollIntoView({ block: 'nearest' })
  }

  function onKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    if (!active) {
      return
    }
    const at = items.indexOf(active)
    const moves: Record<string, number> = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: items.length - 1 }
    if (event.key in moves) {
      event.preventDefault()
      activate(items[Math.max(0, Math.min(items.length - 1, moves[event.key]))])
    } else if (event.key === 'Enter') {
      if (active.opens) {
        event.preventDefault()
        onOpen?.(active.id)
      }
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      // Typing a name jumps to the first row that starts with what was typed
      const now = Date.now()
      const text = (now - typed.current.at < TYPING_MS ? typed.current.text : '') + plain(event.key)
      typed.current = { text, at: now }
      const match = items.find((item) => plain(item.name).startsWith(text))
      if (match) {
        event.preventDefault()
        activate(match)
      }
    }
  }

  return (
    <div className="map-list">
      <ul
        ref={listbox}
        className="map-list-items"
        role="listbox"
        tabIndex={0}
        aria-label={title}
        aria-describedby={`${id}-instructions`}
        aria-activedescendant={active ? `${id}-${active.id}` : undefined}
        onKeyDown={onKeyDown}
        onFocus={() => active && onShow(active.id)}
        onBlur={() => onShow(null)}
        // The pointer leaving gives the map back to the row the keyboard reached, if the list has the keyboard
        onMouseLeave={() => onShow(listbox.current === document.activeElement && active ? active.id : null)}
      >
        {items.map((item) => (
          <li
            key={item.id}
            id={`${id}-${item.id}`}
            role="option"
            aria-selected={item === active}
            className="map-list-option"
            // The row under the pointer outlines its barangay on the map
            onMouseEnter={() => onShow(item.id)}
            onClick={() => {
              activate(item)
              if (item.opens) {
                onOpen?.(item.id)
              }
            }}
          >
            {item.marker && (
              <span className="map-list-marker" aria-hidden="true">
                {item.marker}
              </span>
            )}
            <span className="map-list-name label-ui">
              {item.name}
              <span className="visually-hidden">: {item.words}</span>
            </span>
            {item.detail && (
              <span className="map-list-detail" aria-hidden="true">
                {item.detail}
              </span>
            )}
          </li>
        ))}
      </ul>
      <p id={`${id}-instructions`} className="visually-hidden">
        {instructions}
      </p>
    </div>
  )
}
