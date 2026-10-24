import { jsPDF } from 'jspdf'
import qrcode from 'qrcode-generator'
import wordmark from '../assets/logo/wordmark-1024.png?inline'
import { shapeMiddle, shapeParts, type LonLat } from '../exposed/nearest.ts'
import type { BarangayShapes } from '../map/planData.ts'
import { tokenColor } from '../map/tokens.ts'
import { reportContent, type ReportContent, type ReportInput, type Table } from './reportContent.ts'
import { boundsOf, contains, fitView, overlaps, pagePoints, ringsOf, scaleKm, type Box, type MapView } from './reportMap.ts'

/* The barangay report as a PDF: a cover, a page of what to stock and where, then the details. */

/** A4 portrait, in mm. */
const PAGE_WIDTH = 210
/** The left and right margins, in mm, and the width between them. */
const MARGIN = 16
const WIDTH = PAGE_WIDTH - 2 * MARGIN
/** Where each page's header sits. */
const HEADER_Y = 11
const CONTENT_TOP = 24
const CONTENT_BOTTOM = 278
const FOOTER_Y = 284
/** Millimetres in a typographic point. */
const PT = 25.4 / 72
/** Lines are this many times their font size apart. */
const LEADING = 1.3
/** Font sizes, in pt. */
const SIZE = { headline: 10, heading: 11, body: 8.5, table: 8, small: 7.5, tiny: 6.5, figure: 18 }
/** The cover's font sizes, in pt; the logo's height, the QR code's side and its top, in mm. */
const COVER = { eyebrow: 9, name: 40, place: 11, storm: 15, line: 10.5, centers: 11, logo: 9, qr: 40, qrTop: 222 }
/** The logo's height in each page's header, in mm, and the name the PDF keeps its one copy of the image under. */
const HEADER_LOGO = 3.4
const LOGO_ALIAS = 'lepton-wordmark'
/** The line under the cover's logo (index.html's description, shortened). */
const TAGLINE = 'Leptospirosis forecasts and prophylaxis stock planning for Quezon City'
/** The QR code: its error correction (M: about 15% of it may be lost) and the white border around it, in modules. */
const QR_LEVEL = 'M'
const QR_QUIET = 4
/** Padding inside a table's cell and inside a box, in mm. */
const CELL_PAD = 1.8
const BOX_PAD = 3.5
/** The gap between the stock cards, in mm. */
const CARD_GAP = 4
/** The map: the legend's column beside it, its height between these, filling what is left of page 1. */
const MAP = { column: 48, gap: 5, least: 66, most: 125 }
/** The small map of the city under the legend: at most this tall, and left out below the least. */
const LOCATOR = { most: 34, least: 18 }
/** The map shows at least this many km across. */
const MAP_MIN_KM = 1.5
const MAP_PAD = 0.3
/** The shortest step the outlines keep, in mm: on the map, and on the small map of the city. */
const MAP_STEP_MM = 0.12
const LOCATOR_STEP_MM = 0.3
/** The tag beside the stock's heading. */
const STOCK_TAG = 'STOCK PLANNING, NOT PRESCRIPTIONS'

/** The characters past Latin-1 that a PDF's Helvetica prints (Windows-1252's, WinAnsiEncoding). */
const WIN_ANSI_EXTRAS = '€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ'

/** The colors the PDF draws with: the app's tokens, as #rrggbb. */
export type ReportColors = {
  text: string
  secondary: string
  tertiary: string
  accent: string
  accentSubtle: string
  border: string
  borderStrong: string
  raised: string
  surface: string
  land: string
  warn: string
  alert: string
  alertSubtle: string
  /** The map's five classes, light to dark: --color-data-ramp-1 to -5. */
  ramp: string[]
}

/** Each color's token in tokens.css (--color-<token>). */
export const COLOR_TOKENS: Record<Exclude<keyof ReportColors, 'ramp'>, string> = {
  text: 'text-primary',
  secondary: 'text-secondary',
  tertiary: 'text-tertiary',
  accent: 'accent-primary',
  accentSubtle: 'accent-subtle',
  border: 'border-subtle',
  borderStrong: 'border-strong',
  raised: 'bg-raised',
  surface: 'bg-surface',
  land: 'map-land',
  warn: 'status-warn',
  alert: 'status-alert',
  alertSubtle: 'risk-high',
}

/** The tokens of the map's five classes. */
export const RAMP_TOKENS = [1, 2, 3, 4, 5].map((step) => `data-ramp-${step}`)

/** The report's colors from the page's tokens. */
function pageColors(): ReportColors {
  const root = document.documentElement
  const canvas = document.createElement('canvas').getContext('2d')
  if (!canvas) {
    throw new Error('the browser gives no canvas to read the report’s colors with')
  }
  const color = (token: string) => {
    const value = tokenColor(root, token)
    if (CSS.supports('color', value)) {
      canvas.fillStyle = value
    }
    const hex = String(canvas.fillStyle)
    if (!CSS.supports('color', value) || !/^#[0-9a-f]{6}$/i.test(hex)) {
      throw new Error(`tokens.css: --color-${token} is "${value}", not an opaque color the report can draw`)
    }
    return hex
  }
  const named = Object.fromEntries(Object.entries(COLOR_TOKENS).map(([key, token]) => [key, color(token)]))
  return { ...(named as Omit<ReportColors, 'ramp'>), ramp: RAMP_TOKENS.map(color) }
}

/** Stops with an error naming any character a PDF's Helvetica cannot print. */
function assertPrintable(text: string) {
  for (const char of text) {
    const code = char.codePointAt(0) ?? 0
    const latin1 = (code >= 0x20 && code <= 0x7e) || (code >= 0xa0 && code <= 0xff)
    if (!latin1 && !WIN_ANSI_EXTRAS.includes(char)) {
      const hex = code.toString(16).toUpperCase().padStart(4, '0')
      throw new Error(`The report cannot print "${char}" (U+${hex}) in "${text}": use a Latin-1 or Windows-1252 character`)
    }
  }
}

/** A color mixed with white: `amount` 0 is white, 1 the color. */
function tint(hex: string, amount: number): string {
  const mix = (at: number) => {
    const value = parseInt(hex.slice(at, at + 2), 16)
    return Math.round(255 - (255 - value) * amount)
      .toString(16)
      .padStart(2, '0')
  }
  return `#${mix(1)}${mix(3)}${mix(5)}`
}

/** The logo: a PNG data URL, and its width over its height. */
type Logo = { data: string; ratio: number }

/** The PDF being drawn, its colors, the logo, and what each page's header says. */
type Pen = { doc: jsPDF; colors: ReportColors; logo: Logo; name: string; made: string; y: number }

/** Sets the font for the text that follows: Helvetica, `size` pt, plain or bold, in `color`. */
function font(pen: Pen, size: number, style: 'normal' | 'bold', color: string) {
  pen.doc.setFont('helvetica', style)
  pen.doc.setFontSize(size)
  pen.doc.setTextColor(color)
}

/** A line's height in mm, for text of `size` pt. */
function lineHeight(size: number): number {
  return size * PT * LEADING
}

/** Text broken into lines no wider than `width` mm, in the font set last. */
function wrap(pen: Pen, text: string, width: number): string[] {
  assertPrintable(text)
  return pen.doc.splitTextToSize(text, width) as string[]
}

/** Writes lines with the first one's top at y; `align` right or center puts their ends or middles at x. */
function write(pen: Pen, lines: string[], x: number, y: number, align: 'left' | 'right' | 'center' = 'left') {
  lines.forEach(assertPrintable)
  pen.doc.text(lines, x, y, { baseline: 'top', align, lineHeightFactor: LEADING })
}

/** A new page with its header; the pen goes to the top of its content. */
function newPage(pen: Pen) {
  pen.doc.addPage()
  drawHeader(pen)
  pen.y = CONTENT_TOP
}

/** Starts a new page unless `height` mm still fit on this one. */
function ensure(pen: Pen, height: number) {
  if (pen.y + height > CONTENT_BOTTOM) {
    newPage(pen)
  }
}

type ParagraphStyle = { size?: number; style?: 'normal' | 'bold'; color?: string; after?: number; indent?: number }

/** A paragraph's lines and height in mm (with `after`), in its style, before it is written. */
function measure(pen: Pen, text: string, { size = SIZE.body, style = 'normal', after = 1.6, indent = 0 }: ParagraphStyle) {
  font(pen, size, style, pen.colors.text)
  const lines = wrap(pen, text, WIDTH - indent)
  return { lines, height: lines.length * lineHeight(size) + after }
}

/** A paragraph across the page at the pen, moved whole to the next page if it does not fit. */
function paragraph(pen: Pen, text: string, options: ParagraphStyle = {}) {
  const { size = SIZE.body, style = 'normal', color = pen.colors.text, indent = 0 } = options
  const { lines, height } = measure(pen, text, options)
  ensure(pen, lines.length * lineHeight(size))
  font(pen, size, style, color) // again: a new page's header sets its own
  write(pen, lines, MARGIN + indent, pen.y)
  pen.y += height
}

/** The room a heading takes, in mm: the space above it, its line and the space below. */
const HEADING_ROOM = 5 + lineHeight(SIZE.heading) + 2

/** A section's heading, with a short teal bar at its left and an optional tag at the right. */
function heading(pen: Pen, text: string, keepWith: number, tag?: string) {
  ensure(pen, HEADING_ROOM + keepWith)
  pen.y += 5
  const { doc, colors } = pen
  doc.setFillColor(colors.accent)
  doc.rect(MARGIN, pen.y + 0.3, 1, lineHeight(SIZE.heading) - 1.2, 'F')
  font(pen, SIZE.heading, 'bold', colors.text)
  write(pen, [text], MARGIN + 3, pen.y)
  if (tag) {
    font(pen, SIZE.tiny, 'bold', colors.warn)
    write(pen, [tag], MARGIN + WIDTH, pen.y + 1, 'right')
  }
  pen.y += lineHeight(SIZE.heading) + 2
}

/** Draws the logo `height` mm tall with its top left corner at x, y; returns its width in mm. */
function drawLogo(pen: Pen, x: number, y: number, height: number): number {
  const width = height * pen.logo.ratio
  pen.doc.addImage(pen.logo.data, 'PNG', x, y, width, height, LOGO_ALIAS, 'FAST')
  return width
}

/** Each page's header after the cover: the logo, what the report is and for whom, and when it was made. */
function drawHeader(pen: Pen) {
  const { doc, colors } = pen
  const brand = drawLogo(pen, MARGIN, HEADER_Y - 1.9, HEADER_LOGO)
  font(pen, 8, 'normal', colors.secondary)
  write(pen, [`Barangay prophylaxis stock report for ${pen.name}`], MARGIN + brand + 3, HEADER_Y - 1.45)
  font(pen, SIZE.small, 'normal', colors.tertiary)
  write(pen, [pen.made], MARGIN + WIDTH, HEADER_Y - 1.3, 'right')
  doc.setDrawColor(colors.border)
  doc.setLineWidth(0.25)
  doc.line(MARGIN, HEADER_Y + 5, MARGIN + WIDTH, HEADER_Y + 5)
}

/** Every page's footer but the cover's, once all the pages are drawn: the stock-planning label and the page number. */
function drawFooters(pen: Pen, label: string) {
  const { doc, colors } = pen
  const pages = doc.getNumberOfPages()
  for (let page = 2; page <= pages; page++) {
    doc.setPage(page)
    doc.setDrawColor(colors.border)
    doc.setLineWidth(0.25)
    doc.line(MARGIN, FOOTER_Y - 2.5, MARGIN + WIDTH, FOOTER_Y - 2.5)
    font(pen, SIZE.tiny, 'normal', colors.tertiary)
    write(pen, wrap(pen, label, WIDTH - 28), MARGIN, FOOTER_Y)
    write(pen, [`Page ${page} of ${pages}`], MARGIN + WIDTH, FOOTER_Y, 'right')
  }
}

/** A QR code `size` mm square at x, y that opens `url`, drawn as squares so it prints sharp; it is a link too. */
function drawQr(pen: Pen, url: string, x: number, y: number, size: number) {
  const { doc, colors } = pen
  const qr = qrcode(0, QR_LEVEL)
  qr.addData(url)
  qr.make()
  const count = qr.getModuleCount()
  const cell = size / (count + 2 * QR_QUIET)
  doc.setFillColor(colors.surface)
  doc.rect(x, y, size, size, 'F')
  doc.setFillColor(colors.text)
  // Each row's dark modules as runs, a little taller than a module so no hairline shows between rows
  for (let row = 0; row < count; row++) {
    let col = 0
    while (col < count) {
      if (!qr.isDark(row, col)) {
        col++
        continue
      }
      const start = col
      while (col < count && qr.isDark(row, col)) {
        col++
      }
      doc.rect(x + (QR_QUIET + start) * cell, y + (QR_QUIET + row) * cell, (col - start) * cell, cell + 0.02, 'F')
    }
  }
  doc.setDrawColor(colors.border)
  doc.setLineWidth(0.3)
  doc.roundedRect(x, y, size, size, 1.2, 1.2, 'S')
  doc.link(x, y, size, size, { url })
}

/** Small capitals, spaced out, at the pen; the pen moves below them. */
function eyebrow(pen: Pen, text: string, size: number, color: string) {
  font(pen, size, 'bold', color)
  pen.doc.setCharSpace(0.4)
  write(pen, [text], MARGIN, pen.y)
  pen.doc.setCharSpace(0)
  pen.y += lineHeight(size) + 2.5
}

/** Text at the pen in one font, wrapped across the page; the pen moves below it. */
function coverText(pen: Pen, text: string, size: number, style: 'normal' | 'bold', color: string, after: number) {
  font(pen, size, style, color)
  const wrapped = wrap(pen, text, WIDTH)
  write(pen, wrapped, MARGIN, pen.y)
  pen.y += wrapped.length * lineHeight(size) + after
}

/** The centers on the cover, as many as fit above the QR code; "and n more" stands for the rest. */
function coverCenters(pen: Pen, names: string[]) {
  const { colors } = pen
  const bottom = COVER.qrTop - 6
  let shown = 0
  for (const name of names) {
    font(pen, COVER.centers, 'bold', colors.text)
    const height = wrap(pen, name, WIDTH).length * lineHeight(COVER.centers) + 1
    const more = shown < names.length - 1 ? lineHeight(COVER.centers) : 0 // Room for "and n more" after it
    if (pen.y + height + more > bottom) {
      break
    }
    coverText(pen, name, COVER.centers, 'bold', colors.text, 1)
    shown++
  }
  if (shown < names.length) {
    coverText(pen, `and ${names.length - shown} more: see Where the stock goes`, COVER.centers, 'normal', colors.secondary, 0)
  }
}

/** The cover: the logo, the barangay, the storm and forecast, the centers it is for, and a QR code to the map. */
function drawCover(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  drawLogo(pen, MARGIN, 24, COVER.logo)
  font(pen, SIZE.body, 'normal', colors.secondary)
  write(pen, [TAGLINE], MARGIN, 24 + COVER.logo + 3.5)
  doc.setDrawColor(colors.border)
  doc.setLineWidth(0.25)
  doc.line(MARGIN, 48, MARGIN + WIDTH, 48)
  pen.y = 80
  eyebrow(pen, 'BARANGAY PROPHYLAXIS STOCK REPORT', COVER.eyebrow, colors.accent)
  coverText(pen, content.name, COVER.name, 'bold', colors.text, 1)
  coverText(pen, content.place, COVER.place, 'normal', colors.secondary, 14)
  coverText(pen, content.storm, COVER.storm, 'bold', colors.text, 1.5)
  coverText(pen, content.forecastLine, COVER.line, 'normal', colors.text, 0.5)
  coverText(pen, content.rainLine, COVER.line, 'normal', colors.secondary, 14)
  eyebrow(pen, 'PREPARED FOR', SIZE.small, colors.tertiary)
  coverCenters(pen, content.centers.names)
  // The QR code and its words, above the cover's foot
  const top = COVER.qrTop
  drawQr(pen, content.link, MARGIN, top, COVER.qr)
  const x = MARGIN + COVER.qr + 7
  const width = WIDTH - COVER.qr - 7
  font(pen, COVER.centers, 'bold', colors.text)
  write(pen, ["Open this forecast on LEPTON's map"], x, top + 6)
  font(pen, SIZE.body, 'normal', colors.secondary)
  write(pen, ["Scan the code with a phone's camera, or open the link:"], x, top + 12)
  font(pen, SIZE.small, 'normal', colors.accent)
  const link = wrap(pen, content.link, width)
  write(pen, link, x, top + 17)
  doc.link(x, top + 17, width, link.length * lineHeight(SIZE.small), { url: content.link })
  // The foot: when it was made, and the stock-planning label
  doc.setDrawColor(colors.border)
  doc.line(MARGIN, 272, MARGIN + WIDTH, 272)
  font(pen, SIZE.body, 'normal', colors.secondary)
  write(pen, [content.made], MARGIN, 275)
  font(pen, SIZE.tiny, 'normal', colors.tertiary)
  write(pen, wrap(pen, content.label, WIDTH - 60), MARGIN, 280)
  font(pen, SIZE.tiny, 'bold', colors.warn)
  const tag = doc.getTextWidth(STOCK_TAG) + 4.4
  doc.setDrawColor(colors.warn)
  doc.setLineWidth(0.3)
  doc.roundedRect(MARGIN + WIDTH - tag, 274.5, tag, 5.4, 0.7, 0.7, 'S')
  write(pen, [STOCK_TAG], MARGIN + WIDTH - tag / 2, 276.05, 'center')
}

/** The status band: a chip, red when the barangay is flagged, and the residents exposed beside it. */
function drawStatus(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  const { flagged, label, headline, text } = content.flag
  const chip = label.toUpperCase()
  font(pen, SIZE.tiny, 'bold', colors.surface)
  const chipWidth = doc.getTextWidth(chip) + 4
  const chipHeight = 4.8
  const left = MARGIN + BOX_PAD + 1.2 + chipWidth + 3.5
  font(pen, SIZE.small, 'normal', colors.secondary)
  const lines = wrap(pen, text, MARGIN + WIDTH - BOX_PAD - left)
  const height = 2 * BOX_PAD + lineHeight(SIZE.headline) + 0.6 + lines.length * lineHeight(SIZE.small)
  ensure(pen, height)
  doc.setFillColor(flagged ? tint(colors.alert, 0.08) : colors.raised)
  doc.roundedRect(MARGIN, pen.y, WIDTH, height, 1.5, 1.5, 'F')
  doc.setFillColor(flagged ? colors.alert : colors.borderStrong)
  doc.rect(MARGIN, pen.y, 1.2, height, 'F')
  doc.setFillColor(flagged ? colors.alert : colors.secondary)
  doc.roundedRect(MARGIN + BOX_PAD + 1.2, pen.y + BOX_PAD, chipWidth, chipHeight, 0.7, 0.7, 'F')
  font(pen, SIZE.tiny, 'bold', colors.surface)
  write(pen, [chip], MARGIN + BOX_PAD + 1.2 + chipWidth / 2, pen.y + BOX_PAD + 1.25, 'center')
  font(pen, SIZE.headline, 'bold', colors.text)
  write(pen, [headline], left, pen.y + BOX_PAD + 0.2)
  font(pen, SIZE.small, 'normal', colors.secondary)
  write(pen, lines, left, pen.y + BOX_PAD + lineHeight(SIZE.headline) + 0.6)
  pen.y += height
}

/** The stock to prepare: a card per unit, its count large over what it is and who it is for. */
function drawStock(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  const { items, note } = content.stock
  const width = (WIDTH - CARD_GAP * (items.length - 1)) / items.length
  font(pen, SIZE.body, 'bold', colors.text)
  const unitLines = items.map((item) => wrap(pen, item.unit, width - 2 * BOX_PAD))
  const valueHeight = SIZE.figure * PT * 1.15
  const units = Math.max(...unitLines.map((lines) => lines.length))
  const height = 2 * BOX_PAD + valueHeight + 1.2 + units * lineHeight(SIZE.body) + lineHeight(SIZE.small)
  const notes = measure(pen, note, { size: SIZE.small, after: 0 })
  heading(pen, 'Stock to prepare', height + 2 + notes.height, STOCK_TAG)
  items.forEach((item, i) => {
    const x = MARGIN + i * (width + CARD_GAP)
    const top = pen.y
    doc.setDrawColor(colors.border)
    doc.setLineWidth(0.3)
    doc.roundedRect(x, top, width, height, 1.2, 1.2, 'S')
    doc.setFillColor(colors.accent)
    doc.rect(x + 0.15, top, width - 0.3, 0.9, 'F')
    font(pen, SIZE.figure, 'bold', colors.text)
    write(pen, [item.value], x + BOX_PAD, top + BOX_PAD)
    let y = top + BOX_PAD + valueHeight + 1.2
    font(pen, SIZE.body, 'bold', colors.text)
    write(pen, unitLines[i], x + BOX_PAD, y)
    y += units * lineHeight(SIZE.body)
    font(pen, SIZE.small, 'normal', colors.secondary)
    write(pen, [item.who], x + BOX_PAD, y)
  })
  pen.y += height + 2
  paragraph(pen, note, { size: SIZE.small, color: colors.tertiary, after: 0 })
}

/** A table column: its width in mm, which side its text keeps to, and whether its cells are bold. */
type Column = { width: number; align: 'left' | 'right'; bold?: boolean }

/** A table broken into lines. */
type TableLayout = { heads: string[][]; headHeight: number; cells: string[][][]; heights: number[]; height: number }

/** The font of a table's header row. */
function headFont(pen: Pen) {
  font(pen, SIZE.tiny, 'bold', pen.colors.secondary)
}

/** The font of a cell: bold in a bold column or a strong row. */
function cellFont(pen: Pen, bold: boolean) {
  font(pen, SIZE.table, bold ? 'bold' : 'normal', pen.colors.text)
}

/** A table's layout: each cell's text wrapped inside its column. */
function layoutTable(pen: Pen, table: Table, columns: Column[]): TableLayout {
  headFont(pen)
  const heads = table.heads.map((head, i) => wrap(pen, head, columns[i].width - 2 * CELL_PAD))
  const headHeight = Math.max(...heads.map((head) => head.length)) * lineHeight(SIZE.tiny) + 2 * CELL_PAD
  const cells = table.rows.map((row) =>
    row.cells.map((cell, i) => {
      cellFont(pen, Boolean(columns[i].bold || row.strong))
      return wrap(pen, cell, columns[i].width - 2 * CELL_PAD)
    }),
  )
  const heights = cells.map((row) => Math.max(...row.map((cell) => cell.length)) * lineHeight(SIZE.table) + 2 * CELL_PAD)
  return { heads, headHeight, cells, heights, height: headHeight + heights.reduce((sum, each) => sum + each, 0) + 2 }
}

/** One row of a table at the pen: each cell's lines, kept to its column's side. */
function drawRow(pen: Pen, cells: string[][], columns: Column[], setFont: (column: number) => void) {
  let x = MARGIN
  cells.forEach((cell, i) => {
    setFont(i)
    const right = columns[i].align === 'right'
    write(pen, cell, right ? x + columns[i].width - CELL_PAD : x + CELL_PAD, pen.y + CELL_PAD, right ? 'right' : 'left')
    x += columns[i].width
  })
}

/** A table across the page. */
function drawTable(pen: Pen, table: Table, columns: Column[], layout = layoutTable(pen, table, columns)) {
  const { doc, colors } = pen
  ensure(pen, layout.height)
  doc.setFillColor(colors.raised)
  doc.rect(MARGIN, pen.y, WIDTH, layout.headHeight, 'F')
  drawRow(pen, layout.heads, columns, () => headFont(pen))
  pen.y += layout.headHeight
  layout.cells.forEach((row, r) => {
    const strong = Boolean(table.rows[r].strong)
    if (strong) {
      doc.setFillColor(colors.accentSubtle)
      doc.rect(MARGIN, pen.y, WIDTH, layout.heights[r], 'F')
    }
    drawRow(pen, row, columns, (i) => cellFont(pen, Boolean(columns[i].bold) || strong))
    pen.y += layout.heights[r]
    doc.setDrawColor(colors.border)
    doc.setLineWidth(0.2)
    doc.line(MARGIN, pen.y, MARGIN + WIDTH, pen.y)
  })
  pen.y += 2
}

/** Notes under a table, in small type. */
function tableNotes(pen: Pen, notes: string[]) {
  for (const note of notes) {
    paragraph(pen, note, { size: SIZE.small, color: pen.colors.secondary, after: 1 })
  }
}

/** Where the stock goes: how the need reaches the centers, and each center's order. */
function drawCenters(pen: Pen, content: ReportContent) {
  const { intro, table, notes } = content.centers
  // The pin's number, the center's name, then the share (when split) and the three units; the name takes what is left
  const numbers = table.heads.length - 2
  const widths = [6, WIDTH - 6 - 24 * numbers, ...Array.from({ length: numbers }, () => 24)]
  const columns = widths.map((width, i): Column => ({ width, align: i >= 2 ? 'right' : 'left', bold: i === 1 }))
  const layout = layoutTable(pen, table, columns)
  const first = intro ? measure(pen, intro, { after: 2 }).height : 0
  heading(pen, 'Where the stock goes', first + layout.height)
  if (intro) {
    paragraph(pen, intro, { after: 2 })
  }
  drawTable(pen, table, columns, layout)
  tableNotes(pen, notes)
}

/** Traces a shape's rings on the map as one path, each ring a closed part, ready to fill. */
function tracePath(doc: jsPDF, rings: LonLat[][], view: MapView, stepMm: number): boolean {
  let traced = false
  for (const ring of rings) {
    const points = pagePoints(ring, view, stepMm)
    if (points.length < 3) {
      continue
    }
    doc.moveTo(points[0][0], points[0][1])
    for (const [x, y] of points.slice(1)) {
      doc.lineTo(x, y)
    }
    doc.close()
    traced = true
  }
  return traced
}

/** Text with a white halo, so it reads over every shade of the map. */
function haloText(pen: Pen, text: string, [x, y]: [number, number], size: number, style: 'normal' | 'bold') {
  const { doc, colors } = pen
  assertPrintable(text)
  font(pen, size, style, colors.text)
  doc.setDrawColor(colors.surface)
  doc.setLineWidth(0.7)
  doc.setLineJoin('round')
  doc.text(text, x, y, { baseline: 'middle', align: 'center', renderingMode: 'stroke' })
  doc.text(text, x, y, { baseline: 'middle', align: 'center', renderingMode: 'fill' })
}

/** A health center's pin: a dark disc with its number in white, as in the table. */
function drawPin(pen: Pen, [x, y]: [number, number], number: number) {
  pen.doc.setFillColor(pen.colors.text)
  pen.doc.setDrawColor(pen.colors.surface)
  pen.doc.setLineWidth(0.4)
  pen.doc.circle(x, y, 2.1, 'FD')
  font(pen, SIZE.tiny, 'bold', pen.colors.surface)
  pen.doc.text(String(number), x, y, { baseline: 'middle', align: 'center' })
}

/** The north arrow's white patch, at the map's top right. */
function northPatch(box: Box): Box {
  return { x: box.x + box.width - 7.8, y: box.y + 1.8, width: 5.6, height: 10 }
}

/** The north arrow, on its patch. */
function drawNorth(pen: Pen, box: Box) {
  const { doc, colors } = pen
  const patch = northPatch(box)
  const [x, y] = [patch.x + patch.width / 2, patch.y + 1.2]
  doc.setFillColor(colors.surface)
  doc.roundedRect(patch.x, patch.y, patch.width, patch.height, 0.8, 0.8, 'F')
  doc.setFillColor(colors.text)
  doc.triangle(x, y, x - 1.5, y + 3.8, x + 1.5, y + 3.8, 'F')
  font(pen, SIZE.tiny, 'bold', colors.text)
  write(pen, ['N'], x, y + 4.4, 'center')
}

/** The scale bar's length on the map, in km and in mm: a round length at least 12 mm long. */
function scaleBar(view: MapView): { km: number; mm: number } {
  const km = scaleKm(view.mmPerKm, 12)
  return { km, mm: km * view.mmPerKm }
}

/** The scale bar's white patch, at the map's bottom left. */
function scalePatch(box: Box, view: MapView): Box {
  return { x: box.x + 1.7, y: box.y + box.height - 9.1, width: scaleBar(view).mm + 3.6, height: 7.2 }
}

/** The scale bar, on its patch. */
function drawScale(pen: Pen, box: Box, view: MapView) {
  const { doc, colors } = pen
  const { km, mm: length } = scaleBar(view)
  const patch = scalePatch(box, view)
  const x = patch.x + 1.8
  const y = patch.y + 5.6
  doc.setFillColor(colors.surface)
  doc.roundedRect(patch.x, patch.y, patch.width, patch.height, 0.8, 0.8, 'F')
  doc.setDrawColor(colors.text)
  doc.setLineWidth(0.35)
  doc.line(x, y, x + length, y)
  doc.line(x, y - 1.2, x, y)
  doc.line(x + length, y - 1.2, x + length, y)
  font(pen, SIZE.tiny, 'normal', colors.text)
  doc.text(km < 1 ? `${Math.round(km * 1000)} m` : `${km} km`, x + length / 2, y - 1.5, { baseline: 'bottom', align: 'center' })
}

/** Whether two boxes on the page overlap. */
function boxesOverlap(a: Box, b: Box): boolean {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
}

/** The room a pin takes on the page, with a little margin. */
function pinRoom([x, y]: [number, number]): Box {
  return { x: x - 2.8, y: y - 2.8, width: 5.6, height: 5.6 }
}

/** The names on the map. */
function drawNames(pen: Pen, box: Box, view: MapView, shapes: BarangayShapes, content: ReportContent) {
  const { psgc } = content.map
  const pins = content.centers.pins.map((pin) => pinRoom(view.toPage(pin.at)))
  const placed: Box[] = [northPatch(box), scalePatch(box, view), ...pins]
  const features = [...shapes.features].sort((a, b) => Number(b.properties.psgc === psgc) - Number(a.properties.psgc === psgc))
  for (const { properties, geometry } of features) {
    const own = properties.psgc === psgc
    const middle = shapeMiddle(shapeParts(geometry))
    if (!contains(view.bounds, middle)) {
      continue
    }
    const size = own ? SIZE.small : SIZE.tiny
    font(pen, size, own ? 'bold' : 'normal', pen.colors.text)
    const width = pen.doc.getTextWidth(properties.name) + 1
    const height = size * PT + 0.8
    let [x, y] = view.toPage(middle)
    if (own) {
      const under = pins.find((room) => boxesOverlap({ x: x - width / 2, y: y - height / 2, width, height }, room))
      if (under) {
        y = under.y - height / 2 - 0.5
      }
    }
    const room: Box = { x: x - width / 2, y: y - height / 2, width, height }
    const inside =
      room.x > box.x + 1 && room.x + width < box.x + box.width - 1 && room.y > box.y + 1 && room.y + height < box.y + box.height - 1
    if (!inside || placed.some((other) => boxesOverlap(room, other))) {
      continue
    }
    placed.push(room)
    haloText(pen, properties.name, [x, y], size, own ? 'bold' : 'normal')
  }
}

/** The barangay and its neighbours. */
function drawLocalMap(pen: Pen, box: Box, view: MapView, shapes: BarangayShapes, content: ReportContent) {
  const { doc, colors } = pen
  const { psgc, classes } = content.map
  doc.saveGraphicsState()
  doc.rect(box.x, box.y, box.width, box.height, null) // What follows stays inside the map's box
  doc.clip()
  doc.discardPath()
  doc.setFillColor(colors.land)
  doc.rect(box.x, box.y, box.width, box.height, 'F')
  doc.setDrawColor(colors.surface)
  doc.setLineWidth(0.22)
  doc.setLineJoin('round')
  for (const { properties, geometry } of shapes.features) {
    const rings = ringsOf(geometry)
    if (!overlaps(boundsOf(rings.flat()), view.bounds)) {
      continue
    }
    const cls = classes.get(properties.psgc)
    doc.setFillColor(cls === undefined || cls < 0 ? colors.raised : colors.ramp[cls])
    if (tracePath(doc, rings, view, MAP_STEP_MM)) {
      doc.fillStrokeEvenOdd()
    }
  }
  const own = shapes.features.find((feature) => feature.properties.psgc === psgc)
  if (own) {
    doc.setDrawColor(colors.text)
    doc.setLineWidth(0.65)
    if (tracePath(doc, ringsOf(own.geometry), view, MAP_STEP_MM)) {
      doc.stroke()
    }
  }
  drawNames(pen, box, view, shapes, content)
  for (const pin of content.centers.pins) {
    drawPin(pen, view.toPage(pin.at), pin.number)
  }
  drawNorth(pen, box)
  drawScale(pen, box, view)
  doc.restoreGraphicsState()
  doc.setDrawColor(colors.border)
  doc.setLineWidth(0.3)
  doc.rect(box.x, box.y, box.width, box.height, 'S')
}

/** The legend's title, wrapped to its column. */
function legendTitle(pen: Pen): string[] {
  font(pen, SIZE.small, 'bold', pen.colors.text)
  return wrap(pen, 'Share of residents in flooded zones', MAP.column)
}

/** The legend's height in mm: its title, a row per class, then the outline and the pin. */
function legendHeight(pen: Pen, content: ReportContent): number {
  return legendTitle(pen).length * lineHeight(SIZE.small) + 1.5 + 5 * (content.map.legend.length + 2) + 1
}

/** The legend beside the map: the five classes from the darkest, the black outline and the pins. */
function drawLegend(pen: Pen, x: number, top: number, content: ReportContent) {
  const { doc, colors } = pen
  let y = top
  const title = legendTitle(pen)
  font(pen, SIZE.small, 'bold', colors.text)
  write(pen, title, x, y)
  y += title.length * lineHeight(SIZE.small) + 1.5
  const row = (draw: () => void, label: string) => {
    draw()
    font(pen, SIZE.small, 'normal', colors.secondary)
    write(pen, [label], x + 8.5, y + 0.25)
    y += 5
  }
  for (const { cls, label } of [...content.map.legend].reverse()) {
    row(() => {
      doc.setFillColor(colors.ramp[cls])
      doc.setDrawColor(colors.border)
      doc.setLineWidth(0.2)
      doc.rect(x, y, 6, 3.6, 'FD')
    }, label)
  }
  y += 1
  row(() => {
    doc.setDrawColor(colors.text)
    doc.setLineWidth(0.65)
    doc.rect(x, y, 6, 3.6, 'S')
  }, content.name)
  row(() => drawPin(pen, [x + 3, y + 1.8], 1), content.centers.pins.length > 1 ? 'Its health centers' : 'Its health center')
}

/** The small map of all of Quezon City, the barangay in black and the big map's view outlined in teal. */
function drawLocator(pen: Pen, box: Box, shapes: BarangayShapes, psgc: string, local: MapView) {
  const { doc, colors } = pen
  const view = fitView(boundsOf(shapes.features.flatMap(({ geometry }) => ringsOf(geometry).flat())), box, 0.02, 0)
  doc.setDrawColor(colors.surface)
  doc.setLineWidth(0.1)
  for (const { properties, geometry } of shapes.features) {
    doc.setFillColor(properties.psgc === psgc ? colors.text : colors.borderStrong)
    if (tracePath(doc, ringsOf(geometry), view, LOCATOR_STEP_MM)) {
      doc.fillStrokeEvenOdd()
    }
  }
  const [west, south, east, north] = local.bounds
  const [left, top] = view.toPage([west, north])
  const [right, bottom] = view.toPage([east, south])
  doc.setDrawColor(colors.accent)
  doc.setLineWidth(0.4)
  doc.rect(left, top, right - left, bottom - top, 'S')
  font(pen, SIZE.tiny, 'normal', colors.tertiary)
  write(pen, ['Quezon City'], box.x, box.y - lineHeight(SIZE.tiny) - 0.5)
}

/** The barangay on the map, as tall as the rest of the page allows within MAP's limits. */
function drawMap(pen: Pen, content: ReportContent, shapes: BarangayShapes) {
  const left = CONTENT_BOTTOM - pen.y - HEADING_ROOM
  const height = Math.min(MAP.most, left >= MAP.least ? left : MAP.most)
  heading(pen, 'Map', height)
  const own = shapes.features.find((feature) => feature.properties.psgc === content.map.psgc)
  if (!own) {
    throw new Error(`qc_barangays.geojson has no barangay ${content.map.psgc}: rerun python -m src.app_data`)
  }
  const box: Box = { x: MARGIN, y: pen.y, width: WIDTH - MAP.column - MAP.gap, height }
  const points = [...ringsOf(own.geometry).flat(), ...content.centers.pins.map((pin) => pin.at)]
  const view = fitView(boundsOf(points), box, MAP_PAD, MAP_MIN_KM)
  drawLocalMap(pen, box, view, shapes, content)
  const side = box.x + box.width + MAP.gap
  drawLegend(pen, side, pen.y, content)
  // The city's small map fills what the legend leaves, down to its least
  const room = Math.min(LOCATOR.most, height - legendHeight(pen, content) - 6)
  if (room >= LOCATOR.least) {
    const locator: Box = { x: side, y: pen.y + height - room, width: MAP.column, height: room }
    drawLocator(pen, locator, shapes, content.map.psgc, view)
  }
  pen.y += height
}

/** How many units each person gets: a row per unit, a column per flood. */
function drawCounting(pen: Pen, content: ReportContent) {
  const { table, notes } = content.counting
  const floods = table.heads.length - 2
  const [name, who] = [38, 40]
  const columns: Column[] = [
    { width: name, align: 'left', bold: true },
    { width: who, align: 'left' },
    ...Array.from({ length: floods }, (): Column => ({ width: (WIDTH - name - who) / floods, align: 'left' })),
  ]
  const layout = layoutTable(pen, table, columns)
  heading(pen, 'Who gets what', layout.height)
  drawTable(pen, table, columns, layout)
  tableNotes(pen, notes)
}

/** How far a list's text is indented past its number or bullet, in mm. */
const LIST_INDENT = 5

/** A list under its heading, numbered or with bullets; the heading keeps its first item with it. */
function drawList(pen: Pen, title: string, items: string[], numbered: boolean, size = SIZE.table) {
  const itemLines = (text: string) => {
    font(pen, size, 'normal', pen.colors.text)
    return wrap(pen, text, WIDTH - LIST_INDENT)
  }
  heading(pen, title, itemLines(items[0]).length * lineHeight(size))
  items.forEach((text, i) => {
    const lines = itemLines(text)
    ensure(pen, lines.length * lineHeight(size))
    font(pen, size, numbered ? 'bold' : 'normal', numbered ? pen.colors.accent : pen.colors.text)
    write(pen, [numbered ? `${i + 1}.` : '•'], MARGIN, pen.y)
    font(pen, size, 'normal', pen.colors.text)
    write(pen, lines, MARGIN + LIST_INDENT, pen.y)
    pen.y += lines.length * lineHeight(size) + 1.2
  })
}

/** The sources and their licences in small type, at the end. */
function drawSources(pen: Pen, content: ReportContent) {
  const text = measure(pen, content.sources, { size: SIZE.small })
  heading(pen, 'Sources', text.height)
  paragraph(pen, content.sources, { size: SIZE.small, color: pen.colors.secondary, after: 0 })
}

/** The whole report as a PDF, from its content and the barangay shapes, in `colors`, with `logo` (a PNG data URL). */
export function drawReport(content: ReportContent, shapes: BarangayShapes, colors: ReportColors, logo: string): jsPDF {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true })
  doc.setProperties({
    title: content.docTitle,
    subject: content.label,
    author: 'LEPTON',
    creator: 'LEPTON',
    keywords: 'leptospirosis, prophylaxis, stock planning, barangay, Quezon City',
  })
  doc.setLanguage('en-US')
  const { width, height } = doc.getImageProperties(logo)
  const pen: Pen = {
    doc,
    colors,
    logo: { data: logo, ratio: width / height },
    name: content.name,
    made: content.made,
    y: CONTENT_TOP,
  }
  drawCover(pen, content)
  // Page 2: what to stock and where
  newPage(pen)
  drawStatus(pen, content)
  drawStock(pen, content)
  drawCenters(pen, content)
  drawMap(pen, content, shapes)
  // Then the details, from page 3 unless page 2 has already run over
  if (doc.getNumberOfPages() === 2) {
    newPage(pen)
  } else {
    pen.y += 6
    ensure(pen, 40)
  }
  font(pen, SIZE.small, 'bold', colors.tertiary)
  doc.setCharSpace(0.25)
  write(pen, ['DETAILS'], MARGIN, pen.y)
  doc.setCharSpace(0)
  pen.y += lineHeight(SIZE.small) - 3
  drawCounting(pen, content)
  drawList(pen, 'About these numbers', content.about, false)
  drawSources(pen, content)
  drawFooters(pen, content.label)
  return doc
}

/** Makes one barangay's report for the forecast and date the map shows. */
export function saveBarangayReport(input: ReportInput): string {
  const content = reportContent(input)
  drawReport(content, input.shapes, pageColors(), wordmark).save(content.fileName)
  return content.fileName
}
