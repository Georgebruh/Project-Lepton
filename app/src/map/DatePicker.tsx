import { useId } from 'react'
import Icon from '../components/Icon.tsx'
import { formatDay } from './forecast.ts'
import './DatePicker.css'

type DatePickerProps = {
  /** The chosen date, YYYY-MM-DD. */
  value: string
  /** The first and last dates the reader may choose. */
  min: string
  max: string
  /** Called with each new date the reader chooses. */
  onChange: (day: string) => void
}

/**
 * F4: the date picker in the map's breadcrumb bar, Figma "Date" (node 55:378): calendar icon,
 * the date ("Tue 22 Oct 2024") and a chevron. Under it lies the browser's own date field,
 * invisible but covering the whole control: a click opens the browser's calendar, and the
 * keyboard reaches and changes it like any date field.
 */
export default function DatePicker({ value, min, max, onChange }: DatePickerProps) {
  const id = useId()
  return (
    <div className="date-picker">
      <Icon name="calendar" size={16} />
      <span className="label-ui" aria-hidden="true">
        {formatDay(value)}
      </span>
      <Icon name="chevron-down" size={16} />
      <label htmlFor={id} className="visually-hidden">
        Forecast date
      </label>
      <input
        id={id}
        className="date-picker-input"
        type="date"
        value={value}
        min={min}
        max={max}
        required
        onClick={(event) => event.currentTarget.showPicker?.()}
        onChange={(event) => {
          if (event.target.value) {
            onChange(event.target.value)
          }
        }}
      />
    </div>
  )
}
