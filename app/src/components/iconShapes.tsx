import type { ReactNode } from 'react'

/** The 23 icons' names without "icon/" (icon/play is 'play'). */
export const ICON_NAMES = [
  'play',
  'pause',
  'chevron-left',
  'chevron-right',
  'chevron-down',
  'plus',
  'minus',
  'calendar',
  'calendar-ahead',
  'download',
  'upload',
  'arrow-right',
  'layers',
  'info',
  'close',
  'pin',
  'map',
  'chart',
  'no-data',
  'search',
  'cases',
  'capsule',
  'help',
] as const

export type IconName = (typeof ICON_NAMES)[number]

/* Each icon's shapes, copied from its SVG export. */
export const ICON_SHAPES: Record<IconName, ReactNode> = {
  // icon/play, 3:6
  play: <path d="M8 5.5V18.5L18.5 12L8 5.5Z" fill="currentColor" />,
  // icon/pause
  pause: <path d="M9 6V18M15 6V18" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />,
  // icon/chevron-left, 3:9
  'chevron-left': (
    <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />
  ),
  // icon/chevron-right, 3:12
  'chevron-right': (
    <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />
  ),
  // icon/chevron-down, 4:7
  'chevron-down': (
    <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />
  ),
  // icon/plus, 3:15
  plus: (
    <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />
  ),
  // icon/minus, 3:18
  minus: <path d="M5 12H19" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />,
  // icon/calendar, 3:22
  calendar: (
    <>
      <path
        d="M18.5 5.5H5.5C4.39543 5.5 3.5 6.39543 3.5 7.5V18.5C3.5 19.6046 4.39543 20.5 5.5 20.5H18.5C19.6046 20.5 20.5 19.6046 20.5 18.5V7.5C20.5 6.39543 19.6046 5.5 18.5 5.5Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M3.5 10H20.5M8 3V7M16 3V7"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="square"
      />
    </>
  ),
  // icon/calendar-ahead, 16:835
  'calendar-ahead': (
    <>
      <path
        d="M18.5 5.5H5.5C4.39543 5.5 3.5 6.39543 3.5 7.5V18.5C3.5 19.6046 4.39543 20.5 5.5 20.5H18.5C19.6046 20.5 20.5 19.6046 20.5 18.5V7.5C20.5 6.39543 19.6046 5.5 18.5 5.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M3.5 10H20.5M8 3V7M16 3V7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
      />
      <path
        d="M8 15H14M12 17L14 15L12 13"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
      />
    </>
  ),
  // icon/download, 3:25
  download: (
    <path
      d="M12 4V15M17 10L12 15L7 10M5 20H19"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
    />
  ),
  // icon/upload, 3:42
  upload: (
    <path
      d="M12 20V9M17 14L12 9L7 14M5 4H19"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
    />
  ),
  // icon/arrow-right, 3:28
  'arrow-right': (
    <path
      d="M4 12H19M13 18L19 12L13 6"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
    />
  ),
  // icon/layers, 3:32
  layers: (
    <>
      <path d="M12 3.5L20.5 8L12 12.5L3.5 8L12 3.5Z" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M3.5 12.5L12 17L20.5 12.5M3.5 16.5L12 21L20.5 16.5"
        stroke="currentColor"
        strokeWidth="1.75"
      />
    </>
  ),
  // icon/info, 3:36: the usual "i" in a circle, the same circle as icon/help
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.75" />
      <circle cx="12" cy="8" r="1.125" fill="currentColor" />
      <path d="M12 11V16.75" stroke="currentColor" strokeWidth="1.75" />
    </>
  ),
  // icon/close, 3:39
  close: (
    <path
      d="M6 6L18 18M18 6L6 18"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
    />
  ),
  // icon/pin, 3:46
  pin: (
    <>
      <path
        d="M12 21C12 21 5.5 14.8 5.5 10C5.5 8.27609 6.18482 6.62279 7.40381 5.40381C8.62279 4.18482 10.2761 3.5 12 3.5C13.7239 3.5 15.3772 4.18482 16.5962 5.40381C17.8152 6.62279 18.5 8.27609 18.5 10C18.5 14.8 12 21 12 21Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path d="M14 8H10V12H14V8Z" fill="currentColor" />
    </>
  ),
  // icon/map, 16:825
  map: (
    <>
      <path
        d="M3.5 6.5L9 4L15 6.5L20.5 4V17.5L15 20L9 17.5L3.5 20V6.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M9 4V17.5M15 6.5V20" stroke="currentColor" strokeWidth="1.5" />
    </>
  ),
  // icon/chart, 16:830
  chart: (
    <>
      <path d="M3.5 20.5H20.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
      <path d="M4 15L8 12L11.5 14L15.5 8L20 11" stroke="currentColor" strokeWidth="1.5" />
      <path
        opacity="0.18"
        d="M4 12L8 8L11.5 9.5L15.5 4L20 6.5V11.5L15.5 8.5L11.5 14.5L8 12.5L4 15.5V12Z"
        fill="currentColor"
      />
    </>
  ),
  // icon/no-data, 55:293
  'no-data': (
    <>
      <circle cx="12" cy="12" r="8.25" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5.64 5.64L18.36 18.36" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  // A magnifying glass, the map's search
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.75" />
      <path d="M15.5 15.5L20 20" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" />
    </>
  ),
  // icon/cases, 199:1791: past weeks' counts (solid) and next week's forecast (outlined), the panel's tab
  cases: (
    <>
      <path d="M3 20.5H21" stroke="currentColor" strokeWidth="1.75" />
      <path d="M4.5 12.5H8.5V18.5H4.5V12.5Z" fill="currentColor" />
      <path d="M10 8.5H14V18.5H10V8.5Z" fill="currentColor" />
      <path d="M16.25 4.75H19.25V17.75H16.25V4.75Z" stroke="currentColor" strokeWidth="1.5" />
    </>
  ),
  // icon/capsule, 186:819: the prophylaxis plan's tab
  capsule: (
    <>
      <path
        d="M10.6 19.9L19.9 10.6C21.83 8.67 21.83 5.53 19.9 3.6C17.97 1.67 14.83 1.67 12.9 3.6L3.6 12.9C1.67 14.83 1.67 17.97 3.6 19.9C5.53 21.83 8.67 21.83 10.6 19.9Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path d="M8.25 8.25L15.75 15.75" stroke="currentColor" strokeWidth="1.75" />
    </>
  ),
  // icon/help, 193:1453: what the panel's words mean
  help: (
    <>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M9.5 9.75C9.5 8.37 10.62 7.25 12 7.25C13.38 7.25 14.5 8.37 14.5 9.75C14.5 10.9 13.7 11.5 13 11.95C12.4 12.35 12 12.8 12 13.5V14"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path d="M12 16.25V17.25" stroke="currentColor" strokeWidth="2" />
    </>
  ),
}
