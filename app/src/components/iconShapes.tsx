import type { ReactNode } from 'react'

/** The 18 icons' names, as on the Figma Components page without "icon/" (icon/play is 'play'). */
export const ICON_NAMES = [
  'play',
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
] as const

export type IconName = (typeof ICON_NAMES)[number]

/*
 * F3: each icon's shapes, copied from its SVG export on the Figma Components page (the Figma
 * node id is in the comment). They are drawn on a 24 × 24 grid. Two changes from the export:
 * the dark background square is dropped, and every color is currentColor, so an icon takes
 * the text color of the element around it.
 */
export const ICON_SHAPES: Record<IconName, ReactNode> = {
  // icon/play, 3:6
  play: <path d="M8 5.5V18.5L18.5 12L8 5.5Z" fill="currentColor" />,
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
  // icon/info, 3:36
  info: (
    <>
      <path
        d="M17.5 3.5H6.5C4.84315 3.5 3.5 4.84315 3.5 6.5V17.5C3.5 19.1569 4.84315 20.5 6.5 20.5H17.5C19.1569 20.5 20.5 19.1569 20.5 17.5V6.5C20.5 4.84315 19.1569 3.5 17.5 3.5Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M12 11V17M12 7.5V8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="square"
      />
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
}
