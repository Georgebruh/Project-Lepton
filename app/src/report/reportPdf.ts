import { jsPDF } from 'jspdf'
import { shapeMiddle, shapeParts, type LonLat } from '../exposed/nearest.ts'
import type { BarangayShapes } from '../map/planData.ts'
import { tokenColor } from '../map/tokens.ts'
import { reportContent, type ReportContent, type ReportInput, type Table } from './reportContent.ts'
import { boundsOf, contains, fitView, overlaps, pagePoints, ringsOf, scaleKm, type Box, type MapView } from './reportMap.ts'

/* The barangay report as a PDF. */

/** A4 portrait, in mm. */
const PAGE_WIDTH = 210
/** The left and right margins, in mm, and the width between them. */
const MARGIN = 16
const WIDTH = PAGE_WIDTH - 2 * MARGIN
/** Where each page's header sits. */
const HEADER_Y = 11
const CONTENT_TOP = 23
const CONTENT_BOTTOM = 278
const FOOTER_Y = 284
/** Millimetres in a typographic point. */
const PT = 25.4 / 72
/** Lines are this many times their font size apart. */
const LEADING = 1.3
/** Font sizes, in pt. */
const SIZE = { eyebrow: 7.5, title: 24, about: 9, heading: 11, body: 8.5, table: 8, small: 7.5, tiny: 6.5, figure: 17 }
/** Padding inside a table's cell and inside a shaded box, in mm. */
const CELL_PAD = 1.8
const BOX_PAD = 3.5
/** The gap between the key figures, in mm. */
const FIGURE_GAP = 3
/** The map: its height, the legend's column beside it. */
const MAP = { height: 86, column: 48, gap: 5, locator: 34 }
/** The map shows at least this many km across. */
const MAP_MIN_KM = 1.5
const MAP_PAD = 0.3
/** The shortest step the outlines keep, in mm: on the map, and on the small map of the city. */
const MAP_STEP_MM = 0.12
const LOCATOR_STEP_MM = 0.3
/** The words in the header's box, beside the header's title. */
const HEADER_LABEL = 'STOCK PLANNING, NOT PRESCRIPTIONS'

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

/** The PDF being drawn, its colors. */
type Pen = { doc: jsPDF; colors: ReportColors; name: string; y: number }

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
const HEADING_ROOM = 4 + lineHeight(SIZE.heading) + 1.8

/** A section's heading, with a short teal bar at its left. */
function heading(pen: Pen, text: string, keepWith: number) {
  ensure(pen, HEADING_ROOM + keepWith)
  pen.y += 4
  const { doc, colors } = pen
  doc.setFillColor(colors.accent)
  doc.rect(MARGIN, pen.y + 0.3, 1, lineHeight(SIZE.heading) - 1.2, 'F')
  font(pen, SIZE.heading, 'bold', colors.text)
  write(pen, [text], MARGIN + 3, pen.y)
  pen.y += lineHeight(SIZE.heading) + 1.8
}

/** Each page's header: LEPTON. */
function drawHeader(pen: Pen) {
  const { doc, colors } = pen
  font(pen, 9.5, 'bold', colors.accent)
  write(pen, ['LEPTON'], MARGIN, HEADER_Y - 1.7)
  const brand = doc.getTextWidth('LEPTON')
  font(pen, 8, 'normal', colors.secondary)
  write(pen, [`Barangay prophylaxis stock report  ·  ${pen.name}, Quezon City`], MARGIN + brand + 2.5, HEADER_Y - 1.45)
  font(pen, SIZE.tiny, 'bold', colors.warn)
  const width = doc.getTextWidth(HEADER_LABEL) + 4.4
  doc.setDrawColor(colors.warn)
  doc.setLineWidth(0.3)
  doc.roundedRect(MARGIN + WIDTH - width, HEADER_Y - 2.7, width, 5.4, 0.7, 0.7, 'S')
  write(pen, [HEADER_LABEL], MARGIN + WIDTH - width / 2, HEADER_Y - 1.15, 'center')
  doc.setDrawColor(colors.border)
  doc.setLineWidth(0.25)
  doc.line(MARGIN, HEADER_Y + 5, MARGIN + WIDTH, HEADER_Y + 5)
}

/** Every page's footer, once all the pages are drawn. */
function drawFooters(pen: Pen, label: string) {
  const { doc, colors } = pen
  const pages = doc.getNumberOfPages()
  for (let page = 1; page <= pages; page++) {
    doc.setPage(page)
    doc.setDrawColor(colors.border)
    doc.setLineWidth(0.25)
    doc.line(MARGIN, FOOTER_Y - 2.5, MARGIN + WIDTH, FOOTER_Y - 2.5)
    font(pen, SIZE.tiny, 'normal', colors.tertiary)
    write(pen, wrap(pen, label, WIDTH - 28), MARGIN, FOOTER_Y)
    write(pen, [`Page ${page} of ${pages}`], MARGIN + WIDTH, FOOTER_Y, 'right')
  }
}

/** The title: what the report is, the barangay's name, and what it is, under the first page's header. */
function drawTitle(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  font(pen, SIZE.eyebrow, 'bold', colors.accent)
  doc.setCharSpace(0.25)
  write(pen, ['BARANGAY PROPHYLAXIS STOCK REPORT'], MARGIN, pen.y)
  doc.setCharSpace(0)
  pen.y += lineHeight(SIZE.eyebrow) + 0.8
  font(pen, SIZE.title, 'bold', colors.text)
  const name = wrap(pen, content.name, WIDTH)
  write(pen, name, MARGIN, pen.y)
  pen.y += name.length * SIZE.title * PT * 1.15 + 1
  paragraph(pen, content.about, { size: SIZE.about, color: colors.secondary, after: 3 })
}

/** The flag: a chip, red when the barangay is flagged, and the reason beside it. */
function drawFlag(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  const { flagged, label, text: reason } = content.flag
  const chip = label.toUpperCase()
  font(pen, SIZE.tiny, 'bold', flagged ? colors.surface : colors.secondary)
  const chipWidth = doc.getTextWidth(chip) + 4
  const chipHeight = 4.8
  font(pen, SIZE.body, 'normal', colors.text)
  const lines = wrap(pen, reason, WIDTH - chipWidth - 3)
  const height = Math.max(chipHeight, lines.length * lineHeight(SIZE.body))
  ensure(pen, height)
  doc.setFillColor(flagged ? colors.alert : colors.raised)
  doc.roundedRect(MARGIN, pen.y, chipWidth, chipHeight, 0.7, 0.7, 'F')
  font(pen, SIZE.tiny, 'bold', flagged ? colors.surface : colors.secondary)
  write(pen, [chip], MARGIN + chipWidth / 2, pen.y + 1.25, 'center')
  font(pen, SIZE.body, flagged ? 'bold' : 'normal', flagged ? colors.alert : colors.secondary)
  write(pen, lines, MARGIN + chipWidth + 3, pen.y + 0.6)
  pen.y += height + 4
}

/** One paragraph of a shaded box: its text, size, weight and color. */
type BoxPart = { text: string; size: number; style: 'normal' | 'bold'; color: string }

/** A shaded box's paragraphs broken into lines, and the box's height in mm, before it is drawn. */
function layoutBox(pen: Pen, parts: BoxPart[]) {
  const wrapped = parts.map((part) => {
    font(pen, part.size, part.style, part.color)
    return wrap(pen, part.text, WIDTH - 2 * BOX_PAD)
  })
  const text = wrapped.reduce((sum, lines, i) => sum + lines.length * lineHeight(parts[i].size), 0)
  return { wrapped, height: 2 * BOX_PAD + text + 1.4 * (parts.length - 1) }
}

/** A shaded box across the page holding a few paragraphs. */
function shadedBox(pen: Pen, parts: BoxPart[], fill: string, box = layoutBox(pen, parts)) {
  ensure(pen, box.height)
  pen.doc.setFillColor(fill)
  pen.doc.roundedRect(MARGIN, pen.y, WIDTH, box.height, 1.5, 1.5, 'F')
  let y = pen.y + BOX_PAD
  parts.forEach((part, i) => {
    font(pen, part.size, part.style, part.color)
    write(pen, box.wrapped[i], MARGIN + BOX_PAD, y)
    y += box.wrapped[i].length * lineHeight(part.size) + 1.4
  })
  pen.y += box.height + 4
}

/** The key figures: four boxes, each a large number over what it counts, a teal rule on top. */
function drawFigures(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  const count = content.figures.length
  const width = (WIDTH - FIGURE_GAP * (count - 1)) / count
  font(pen, SIZE.small, 'normal', colors.secondary)
  const labels = content.figures.map((figure) => wrap(pen, figure.label, width - 2 * BOX_PAD))
  const tallest = Math.max(...labels.map((label) => label.length))
  const valueHeight = SIZE.figure * PT * 1.15
  const height = 2 * BOX_PAD + valueHeight + 1.5 + (tallest + 1) * lineHeight(SIZE.small)
  ensure(pen, height)
  content.figures.forEach((figure, i) => {
    const x = MARGIN + i * (width + FIGURE_GAP)
    doc.setDrawColor(colors.border)
    doc.setLineWidth(0.3)
    doc.roundedRect(x, pen.y, width, height, 1.2, 1.2, 'S')
    doc.setFillColor(colors.accent)
    doc.rect(x + 0.15, pen.y, width - 0.3, 0.9, 'F')
    font(pen, SIZE.figure, 'bold', colors.text)
    write(pen, [figure.value], x + BOX_PAD, pen.y + BOX_PAD)
    const labelTop = pen.y + BOX_PAD + valueHeight + 1.5
    font(pen, SIZE.small, 'normal', colors.secondary)
    write(pen, labels[i], x + BOX_PAD, labelTop)
    font(pen, SIZE.small, 'normal', colors.tertiary)
    write(pen, [figure.detail], x + BOX_PAD, labelTop + labels[i].length * lineHeight(SIZE.small))
  })
  pen.y += height + 2
  paragraph(pen, content.figuresNote, { size: SIZE.small, color: colors.tertiary, after: 2 })
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

/** A heading with its table under it, and the table's notes. */
function tableSection(pen: Pen, title: string, table: Table, columns: Column[], notes: string[]) {
  const layout = layoutTable(pen, table, columns)
  heading(pen, title, layout.height)
  drawTable(pen, table, columns, layout)
  for (const note of notes) {
    paragraph(pen, note, { size: SIZE.small, color: pen.colors.secondary, after: 1.2 })
  }
}

/** The stock to prepare: a row per unit, who it is for and how it is counted, and a column per flood. */
function drawStock(pen: Pen, content: ReportContent) {
  const floods = content.stock.table.heads.length - 2
  const [name, value] = [34, 23]
  const columns: Column[] = [
    { width: name, align: 'left', bold: true },
    { width: WIDTH - name - value * floods, align: 'left' },
    ...Array.from({ length: floods }, (): Column => ({ width: value, align: 'right', bold: true })),
  ]
  tableSection(pen, 'Stock to prepare', content.stock.table, columns, content.stock.notes)
}

/** The storm's forecasts made 1 to 3 days ahead, the one on the map in bold. */
function drawLeads(pen: Pen, content: ReportContent) {
  const widths = [33, 33, 32, 30, 18, 16, 16]
  const columns = widths.map((width, i): Column => ({ width, align: i >= 4 ? 'right' : 'left' }))
  tableSection(pen, content.leads.title, content.leads.table, columns, [content.leads.note])
}

/** Where the stock goes. */
function drawCenters(pen: Pen, content: ReportContent) {
  const { intro, table, serves, leftOut, note } = content.centers
  const widths = [6, 48, 30, 24, 24, 23, 23]
  const columns = widths.map((width, i): Column => ({ width, align: i >= 3 ? 'right' : 'left', bold: i === 1 }))
  const layout = layoutTable(pen, table, columns)
  const first = measure(pen, intro, { after: 2 })
  heading(pen, 'Where the stock goes', first.height + layout.height)
  paragraph(pen, intro, { after: 2 })
  drawTable(pen, table, columns, layout)
  for (const line of [...serves, ...leftOut]) {
    paragraph(pen, line, { size: SIZE.small, color: pen.colors.secondary, after: 1 })
  }
  paragraph(pen, note, { size: SIZE.small, color: pen.colors.tertiary, after: 2 })
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

/** The legend beside the map: the five classes from the darkest, the black outline and the pins. */
function drawLegend(pen: Pen, x: number, top: number, content: ReportContent) {
  const { doc, colors } = pen
  let y = top
  font(pen, SIZE.small, 'bold', colors.text)
  const title = wrap(pen, 'Share of residents in flooded zones', MAP.column)
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

/** The barangay on the map. */
function drawMap(pen: Pen, content: ReportContent, shapes: BarangayShapes) {
  font(pen, SIZE.tiny, 'normal', pen.colors.tertiary)
  const caption = wrap(pen, content.map.caption, WIDTH)
  heading(pen, 'The barangay on the map', MAP.height + 2 + caption.length * lineHeight(SIZE.tiny))
  const own = shapes.features.find((feature) => feature.properties.psgc === content.map.psgc)
  if (!own) {
    throw new Error(`qc_barangays.geojson has no barangay ${content.map.psgc}: rerun python -m src.app_data`)
  }
  const box: Box = { x: MARGIN, y: pen.y, width: WIDTH - MAP.column - MAP.gap, height: MAP.height }
  const points = [...ringsOf(own.geometry).flat(), ...content.centers.pins.map((pin) => pin.at)]
  const view = fitView(boundsOf(points), box, MAP_PAD, MAP_MIN_KM)
  drawLocalMap(pen, box, view, shapes, content)
  const side = box.x + box.width + MAP.gap
  drawLegend(pen, side, pen.y, content)
  const locator: Box = { x: side, y: pen.y + MAP.height - MAP.locator, width: MAP.column, height: MAP.locator }
  drawLocator(pen, locator, shapes, content.map.psgc, view)
  pen.y += MAP.height + 2
  font(pen, SIZE.tiny, 'normal', pen.colors.tertiary)
  write(pen, caption, MARGIN, pen.y)
  pen.y += caption.length * lineHeight(SIZE.tiny) + 2
}

/** Quezon City's case forecast. */
function drawCity(pen: Pen, content: ReportContent) {
  const { colors } = pen
  const { title, lines, badge } = content.city
  const parts: BoxPart[] = lines.map((text, i) => ({
    text,
    size: SIZE.body,
    style: i === 0 ? 'bold' : 'normal',
    color: i === lines.length - 1 ? colors.secondary : colors.text,
  }))
  if (badge) {
    parts.unshift({ text: badge.toUpperCase(), size: SIZE.tiny, style: 'bold', color: colors.warn })
  }
  const box = layoutBox(pen, parts)
  heading(pen, title, box.height)
  shadedBox(pen, parts, colors.raised, box)
}

/** How far a list's text is indented past its number or bullet, in mm. */
const LIST_INDENT = 5.5

/** A list under its heading, numbered or with bullets; the heading keeps its first item with it. */
function drawList(pen: Pen, title: string, items: string[], numbered: boolean, size = SIZE.body) {
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
    pen.y += lines.length * lineHeight(size) + 1.4
  })
}

/** When and from what the report was made, and the map's address as a link, at the end. */
function drawMade(pen: Pen, content: ReportContent) {
  const { doc, colors } = pen
  pen.y += 2
  paragraph(pen, content.made, { size: SIZE.small, color: colors.tertiary, after: 1 })
  const intro = "To see this forecast on LEPTON's map: "
  font(pen, SIZE.small, 'normal', colors.tertiary)
  const lines = wrap(pen, intro + content.link, WIDTH)
  ensure(pen, lines.length * lineHeight(SIZE.small))
  font(pen, SIZE.small, 'normal', colors.accent)
  write(pen, lines, MARGIN, pen.y)
  doc.link(MARGIN, pen.y, WIDTH, lines.length * lineHeight(SIZE.small), { url: content.link })
  pen.y += lines.length * lineHeight(SIZE.small)
}

/** The whole report as a PDF, from its content and the barangay shapes, in `colors`. */
export function drawReport(content: ReportContent, shapes: BarangayShapes, colors: ReportColors): jsPDF {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true })
  doc.setProperties({
    title: content.docTitle,
    subject: content.label,
    author: 'LEPTON',
    creator: 'LEPTON',
    keywords: 'leptospirosis, prophylaxis, stock planning, barangay, Quezon City',
  })
  doc.setLanguage('en-US')
  const pen: Pen = { doc, colors, name: content.name, y: CONTENT_TOP }
  drawHeader(pen)
  drawTitle(pen, content)
  drawFlag(pen, content)
  shadedBox(
    pen,
    [
      { text: content.storm, size: 10, style: 'bold', color: colors.text },
      { text: content.forecastLine, size: SIZE.body, style: 'normal', color: colors.text },
      { text: content.cityLine, size: SIZE.body, style: 'normal', color: colors.secondary },
    ],
    colors.raised,
  )
  drawFigures(pen, content)
  drawStock(pen, content)
  drawLeads(pen, content)
  drawCenters(pen, content)
  drawMap(pen, content, shapes)
  drawCity(pen, content)
  drawList(pen, 'How these figures were made', content.method, true)
  drawList(pen, 'Limits', content.limits, false)
  drawList(pen, 'Sources', content.sources, false, SIZE.small)
  drawMade(pen, content)
  drawFooters(pen, content.label)
  return doc
}

/** Makes one barangay's report for the forecast and date the map shows. */
export function saveBarangayReport(input: ReportInput): string {
  const content = reportContent(input)
  drawReport(content, input.shapes, pageColors()).save(content.fileName)
  return content.fileName
}
