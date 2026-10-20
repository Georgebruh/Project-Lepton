import { useId, useState, type FormEvent } from 'react'
import Button from '../components/Button.tsx'
import type { GuideBarangay } from './guideData.ts'
import type { NoLocation } from './location.ts'
import { matchPlaces } from './nearest.ts'
import './BarangayPicker.css'

/** How many matching barangays the list shows at once. */
const SHOWN_MATCHES = 8

/** Why the guide asks for a barangay: no location (and why), or the reader chose to change it. */
export type PickerReason = NoLocation | 'change'

/** The line under the heading, by reason. */
const WHY: Record<PickerReason, string> = {
  denied: 'Location is off for this site, so LEPTON can’t see where you are. Type your barangay instead: the list starts from there.',
  unavailable: 'Your phone couldn’t find where you are. Type your barangay instead: the list starts from there.',
  unsupported: 'This browser can’t share your location. Type your barangay instead: the list starts from there.',
  change: 'The list of health centers starts from the barangay you choose.',
}

type BarangayPickerProps = {
  barangays: GuideBarangay[]
  reason: PickerReason
  /** Called with the PSGC of the barangay the reader picks. */
  onPick: (psgc: string) => void
  /** "Use my location": shown only when asking the phone again can work. */
  onUseLocation?: () => void
  /** "Cancel": back to the list already shown. */
  onCancel?: () => void
}

/**
 * F8: "Type your barangay" (the guide's notes), for a reader who declines to share their location
 * or whose phone cannot tell it, and for "Change". As the reader types, the matching barangays
 * appear as buttons (nearest.ts matchPlaces: accents, dots and "Sto." do not matter); Enter picks
 * the first. Not in Figma: built from the app's tokens and components.
 */
export default function BarangayPicker({ barangays, reason, onPick, onUseLocation, onCancel }: BarangayPickerProps) {
  const id = useId()
  const [typed, setTyped] = useState('')
  const matches = matchPlaces(barangays, typed, barangays.length)
  const shown = matches.slice(0, SHOWN_MATCHES)

  function pickFirst(event: FormEvent) {
    event.preventDefault()
    if (shown.length > 0) {
      onPick(shown[0].psgc)
    }
  }

  let count = ''
  if (typed.trim() !== '') {
    if (matches.length === 0) {
      count = `No barangay matches “${typed.trim()}”. Check the spelling.`
    } else if (matches.length > shown.length) {
      count = `${matches.length} barangays match; the first ${shown.length} are shown.`
    } else {
      count = matches.length === 1 ? '1 barangay matches.' : `${matches.length} barangays match.`
    }
  }

  return (
    <section className="barangay-picker" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`} className="heading-s">
        Type your barangay
      </h2>
      <p className="barangay-picker-why body-m">{WHY[reason]}</p>
      <form className="barangay-picker-form" onSubmit={pickFirst} role="search">
        <label htmlFor={`${id}-input`} className="label-ui">
          Barangay
        </label>
        <input
          id={`${id}-input`}
          className="barangay-picker-input body-m"
          type="text"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          autoComplete="off"
          autoCapitalize="words"
          spellCheck={false}
          enterKeyHint="search"
          aria-describedby={`${id}-count`}
        />
      </form>
      <p id={`${id}-count`} className="barangay-picker-count body-s" aria-live="polite">
        {count}
      </p>
      {shown.length > 0 && (
        <ul className="barangay-picker-matches">
          {shown.map(({ psgc, name }) => (
            <li key={psgc}>
              <button type="button" className="barangay-picker-match label-ui" onClick={() => onPick(psgc)}>
                {name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {(onUseLocation || onCancel) && (
        <div className="barangay-picker-actions">
          {onUseLocation && (
            <Button variant="secondary" onClick={onUseLocation}>
              Use my location
            </Button>
          )}
          {onCancel && (
            <Button variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      )}
    </section>
  )
}
