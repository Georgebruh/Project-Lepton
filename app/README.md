# LEPTON app (Workstream F)

The LEPTON web app: React and TypeScript on Vite, React Router for the screens and MapLibre GL
JS for the map. It is a static site with no server: `python -m src.app_data` (F2) writes every
number to small JSON files in `public/data/`, and the app only draws them.

## Run it

Needs Node.js 22.12 or newer (`node --version`); Vite 8 and MapLibre need it. From this
folder:

```
npm install      # once, and again after package.json changes
npm run dev      # http://localhost:5173, reloads when you save
```

| Command | What it does |
| --- | --- |
| `npm run build` | Type-checks, then writes the site to `dist/` (not in git) |
| `npm run preview` | Serves `dist/` at http://localhost:4173, as Vercel will |
| `npm run lint` | Oxlint, the code checker |

Versions are pinned in `package.json`; `package-lock.json` pins the rest. Commit both after
adding a package (`npm install --save-exact <name>@<version>`).

## Where things are

| Path | What |
| --- | --- |
| `src/router.tsx` | The routes: which screen each address shows |
| `src/screens/` | One file per screen |
| `src/components/` | The shared components (F3), shown together at `/kit` in `npm run dev` |
| `src/exposed/` | The exposure guide's parts (F8): its three steps, the map and the barangay search; `risk.ts` holds the questions and the risk rule, `nearest.ts` the distances and the search, `location.ts` the phone's position |
| `src/compare/` | Compare models' parts (F9): the chart (`CompareChart.tsx`), its tooltip, keys and table view, the Controls panel and the scores; `periods.ts` holds the three periods and the x axis, `models.ts` each model's name, color and line, `chartGeometry.ts` the chart's sizes and paths, `compareData.ts` its loader. F18: Compare models has left the map's panel and moves into How it works; until then no screen shows these parts |
| `src/map/` | The map's parts (F4): the map, its legend, zoom buttons, date picker and city panel; `routes.ts` names the three levels. F5's prophylaxis plan: the barangays on the map (`barangayLayers.ts`), its panel, legend and tooltip, and `plan.ts`, which reads its files. F11: `MapList.tsx`, the list that reaches every barangay from the keyboard. F14: `MapDataModes.tsx` (Simulation \| Real data, top right), `MapTimeline.tsx` (the week, bottom middle), `MapSearch.tsx` (the search beside the logo), `borders.ts` (which lines show at each zoom), `orbit.ts` (the plan's circling camera). F15: `BarangayPopup.tsx`, the pop-up a click on a barangay opens. F18: `EdgeTabs.tsx` (the panel's two tabs on its right edge), `Facts.tsx` (the panel's label and value rows), `WordHelp.tsx` (the ? and what the words mean), `MapInfo.tsx` (the info button: Methods, the data note and the credits) |
| `src/report/` | F15's barangay report, a PDF made in the browser: `reportContent.ts` (its words and tables, from the files), `reportPdf.ts` (draws them with jsPDF and saves the file), `reportMap.ts` (its maps' geometry) |
| `src/home/` | Home's parts (F6): the plan's preview (`PlanPreview.tsx`), the city forecast's chart (`BacktestChart.tsx`), the photos and their credits (`photos.ts`), the hero's waterlines (`waterlines.ts`, F17) and the files it loads (`homeData.ts`) |
| `src/motion/` | F17: the reveal on scroll (`reveal.ts`), the numbers that count up (`CountUp.tsx`) and the glide of in-page links (`smoothLinks.ts`) |
| `src/assets/` | Images the code imports; Vite gives each a hashed name under `/assets/` (F6: Home's photos). `logo/` holds PNGs of the logo for the paper and slides (the wordmark and its O, 1024 px, transparent, light theme colors); nothing imports them, so they are not in the build |
| `src/styles/tokens.css` | Every color, corner radius, spacing step and text style, from Figma |
| `src/styles/global.css` | Page-wide base styles |
| `src/styles/motion.css` | F17: the durations and curves of every animation, and the reveal on scroll |
| `src/lib/maplibre.ts` | MapLibre, set up for Vite; map code imports it from here |
| `public/data/` | F2's data files, fetched as `/data/<file>` |
| `public/favicon.svg`, `public/robots.txt` | The browser tab's icon, the logo's O, and the note for search engines (F12); served as they are |
| `vercel.json` | Sends every screen's address to the app on Vercel |
| `vite.config.ts` | Vite's settings; a missing `/data/` file answers 404 here too, as on Vercel |

## Screens

The map levels share `MapLayout.tsx`, so the one map stays on screen while the reader drills
down; each level's own content shows inside it. Figma node ids are in each file. F14: the map is
the app's one view, with no other tabs. F18: the panel has two tabs, Cases forecast and
Prophylaxis plan; Compare models has left it for How it works.

| Route | Screen | File | Task |
| --- | --- | --- | --- |
| `/` | Home | `Home.tsx` | F6 |
| `/map` | Map: the Philippines | `MapPhilippines.tsx` | F4, F14 |
| `/map/quezon-city` | Map: Quezon City's case forecast | `MapQuezonCity.tsx` | F4 |
| `/map/quezon-city/prophylaxis` | Map: prophylaxis plan; F15: a barangay's pop-up and report | `MapProphylaxis.tsx` | F5, F15 |
| `/leptospirosis` | Leptospirosis, for residents | `Leptospirosis.tsx` | F7 |
| `/exposed` | The "I have been exposed to floodwater" guide | `Exposed.tsx` | F8 |
| `/compare`, `/map/quezon-city/compare` | Compare models' old addresses: open How it works' Models part, `/how-it-works#models`, until Compare models moves there (the site header's Results goes there too) | `CompareRedirect.tsx` | F14, F18 |
| `/how-it-works` | How it works | `HowItWorks.tsx` | F10 |

Any other address, and any error while drawing a screen, shows `ErrorPage.tsx`. Every screen is
built, so F1's placeholder screen is gone (F12).

A setting kept in the address's query should change with
`setSearchParams(next, { preventScrollReset: true })`; otherwise the page jumps to the top.
The map keeps its date there: `/map/quezon-city?date=2024-10-22` (F4). The date picks the
forecast day, the MMWR week holding it, and the panel shows the forecast made that week for
the week after ("next week"); without a date the map shows today's (F14), and a date outside
the dates the mode has moves inside them. Links between the map levels keep it
(`MAP_PATHS[2] + search`). The map keeps its data mode there too, `?data=real` (F14), and the
prophylaxis plan the forecast picked, `?lead=2` (F5).

## Components

`src/components/` holds the pieces every screen shares, built from the Figma Components page
(F3). Use them instead of drawing your own button or badge, so the screens stay alike. Open
http://localhost:5173/kit to see each one in every variant; choose Monsoon there to compare
them with the Figma page, which is drawn in that theme. The kit is in `npm run dev` only: its
sample text and buttons that do nothing must not ship (check U7), so the built site answers
`/kit` with the page-not-found screen (F12).

| Component | Use | Figma |
| --- | --- | --- |
| `Button` | `<Button variant="secondary" icon="arrow-right" to="/map">Try LEPTON</Button>`; `to` for a route, `href` for another site (a new tab; `tel:` and `mailto:` open in place), `onClick` otherwise | Button, 3:65 |
| `Badge` | `<Badge tone="warn">Simulated until QCESD data</Badge>`; tones neutral, accent, warn, alert | Badge, 3:78 |
| `Tab` | `<Tab to="/map">Map</Tab>` is selected on its route; `<Tab selected onClick={...}>` otherwise. With both, `selected` wins (F4's panel tabs). `<Tab href="#models" selected={...}>` links to a part of the same page (F10) | Tab, 3:83 |
| `ToggleRow` | `<ToggleRow label="M3" on={on} onChange={setOn} color="var(--color-chart-m3)" />` | Toggle row, 3:94 |
| `StatCard` | `<StatCard label="Residents exposed" value="789,689" caption="..." />` | Stat card, 4:8 |
| `CenterRow` | One health center's doxycycline, children's courses and amoxicillin; rows go in a `role="table"`, under `<CenterRowHeader />`, the column names (F6, as in Home's stock list) | Center row, 4:12 |
| `PanelHeader` | A side-panel section's title that opens and closes it | Panel header, 4:17 |
| `SiteHeader` | The header of Home, Leptospirosis and How it works; the open page's link is darker (F6). Below 1024 px the links wrap on a row of their own | Site header, 4:21 |
| `Footer` | The footer, with the stock-planning note and the credits of the app's data and fonts, each with its licence (F12, check U8); `credits` adds the page's own under them (F6: Home's photos) | Home frame, 20:364 |
| `Logo` | The logo; the headers and the footer already include it | Logo, 3:47 |
| `Icon` | `<Icon name="calendar" size={16} />`, any of the 18 Figma icons, in the text color | icon/…, Components page |

Each component's CSS starts its classes with the component's name (`.button-primary` in
`Button.css`). In Figma, the 1 px border of the Secondary button and the Selected tab adds to
their size, so they are 2 px larger than the others (46 px tall, not 44); the CSS does the
same. A row of tabs therefore lines them up at the top (`align-items: flex-start`). The logo is
concept G from the Figma page "Logo concepts": the wordmark in Instrument Sans SemiBold, as in
the Figma Logo, with a drawn ripple (concept F) for its O; `index.html` loads only the five
letters it sets. Every other text is Figtree.

## Data (F2)

`python -m src.app_data`, run from the repository root, writes the data files into
`public/data/`. The app fetches them as `/data/<file>` and computes nothing but map styling
and distances. Barangays and cities join on the 10-digit PSGC (`psgc`, a string). Rerun it
whenever C8, C9, B10 or A8 change, then commit the files.

| File | What it holds | Screens |
| --- | --- | --- |
| `ph_cities.json` | F14: the Philippines' 1,642 cities and municipalities (faeldon's 2023 maps): `psgc`, `name`, `province`, `has_data` (Quezon City only), and `label_lon`, `label_lat` where the map writes the name of a city with data (Quezon City only; the street map names the rest). NCR's 17 are F4's cleaned outlines; the rest are simplified province by province to about 100 m (`config.PH_SIMPLIFY_M`). 6 MB, 1.4 MB sent compressed (it is `.json`, not `.geojson`, so Vercel compresses it). It replaces F4's `ncr_cities.geojson` | Map |
| `ph_islands.json` | F14: the coastline of every island of 1 km² or more (`config.PH_ISLANDS_MIN_KM2`): the 1,642 towns joined, the gaps between faeldon's province files closed (`PH_ISLANDS_GAP_M`), each island's outer coast only (the holes left are lakes, which the street map draws, or gaps in faeldon's maps), simplified to 250 m (`PH_ISLANDS_SIMPLIFY_M`). 0.5 MB, 0.15 MB sent compressed | Map |
| `qc_barangays.geojson` | Quezon City's 142 barangays: `psgc`, `name` | Map, Home |
| `noah_flood_5yr.pmtiles`, `noah_flood_25yr.pmtiles`, `noah_flood_100yr.pmtiles` | F14: NOAH's flood maps of every province NOAH has mapped, as vector tiles (`python -m src.noah_national`, not F2): layer `flood`, `var` 1 low (up to 0.5 m), 2 medium (0.5–1.5 m), 3 high (over 1.5 m), zooms 4 to 11, each map thinned as little as keeps it under GitHub's 100 MB a file (`config.NOAH_TILE_LIMITS`: the 5- and 25-year maps keep tippecanoe's default tiles; the 100-year map's densest tiles drop more of their smallest patches). Patches under 400 m² dropped. ODbL, as NOAH's maps are. 50–95 MB each; the browser fetches only the tiles in view (HTTP range requests). They replace F13's Metro Manila overlays, `noah_<T>yr.json` | Map's flood zones (F13, F14), read when first turned on |
| `noah_barangays/<T>yr/<psgc>.json` | F13: one barangay's zones on one NOAH map (`python -m src.noah_barangays`, not F2), drawn instead of the tiles while its pop-up is open: A8's Metro Manila maps, patches under 400 m² dropped as for the tiles, simplified together to about 10 m (`config.APP_NOAH_BARANGAY_SIMPLIFY_M`, one cell of NOAH's grid) and cut along `qc_barangays.geojson`'s outlines; one row per `var`, points to 6 decimals (`APP_NOAH_BARANGAY_DECIMALS`). A file for every barangay, empty where it has no zones. 3.1–3.5 MB a map, about 25 kB a barangay (at most 0.4 MB) | Prophylaxis plan, read when a barangay opens with the zones on |
| `storms.json` | Per storm and run (`observed`, `lead 1` to `lead 3`): `window`, `issued`, `rain_mm`, `position` against the return levels, `ei_pct`, `flagged`; per flood (`D1` is D = 1 at w = 0.5, `D7` is 7 days; the observed run has A11's D): `exposed` and the units. Also the five map `classes`, and (F15) `counting`, C6's units per person from `config.py`, which the barangay report explains | Prophylaxis plan |
| `barangays/<storm>_<run>.json` | Per barangay: `exposed`, `share`, `class` (0 to 4: `--color-data-ramp-1` to `-5`), `flagged`, `units` per flood | Prophylaxis plan, Home |
| `days/<year>.json` | F16: a prophylaxis plan for every day (`python -m src.app_days`, not F2), one file per year, fetched when the date first reaches that year. Each day in `storms.json`'s form (key `day_<date>`, `D` null) for the 3 days of rain from that date: its forecasts made 1 to 3 days before (ECMWF, Open-Meteo's Previous Runs archive, from February 2024; later in the week the newest forecast), or before the archive the rain that fell (IMERG). Also `needs[day][run][flood][facility_code]` for the runs that expose anyone; the others need nothing (`withDayNeeds` in `map/plan.ts`). Most days' rain is below R0: all zeros, no stock. 0.25–0.9 MB a year, 30–60 kB sent compressed | Prophylaxis plan |
| `barangays/days/<date>_<run>.json` | F16: each daily run that exposes anyone (141 of 5,198), in the barangay files' form; every other run points to `barangays/days/no_flood.json`, all 142 at 0 | Prophylaxis plan |
| `centers.json` | Health centers (`lat`, `lon`, `barangay`; `left_out` says why one gets no stock), `needs[storm][run][flood][facility_code]` and (F15) `barangay_centers[psgc]`: the centers that hold each barangay's stock, as C7 sends it (`center_shares_qc.csv`): `rule` `own`, `split` (by who lives nearest each, with its `share`) or `nearest` (with the `km` from the barangay's centroid) | Prophylaxis plan, Exposure guide |
| `city_forecast.json` | Per target week: `start`, `end`, `y`, `threshold`, `breached`, and per model `mu`, `low` and `high` (the 90% range), `p_breach`. `"simulated": true` until A13's counts arrive. Also `map_model` (M4, the model the map shows) and the outbreak `levels`, each with the Pr(breach) it starts at (`config.APP_LEVELS`) | Map, Compare models |
| `city_simulation.json` | F14: the map's Simulation mode (`python -m src.app_simulation`, not F2): the weeks after QCESD's last count, in `city_forecast.json`'s form, to next week. Each ended week's `y` is made up (the median of M4's forecast), `null` for this week and next; `made_on`, the day it ran to, and `weather`, the ECMWF forecast it used. Run it again on a later day to move it | Map in Simulation mode |
| `scores.json` | Per model: MAE, MASE, WIS, 90% coverage, Brier score; D5's M4 − M3 (`primary`). Written only after B10's real run: show "—" while it is missing | Compare models |

Units: `doxy100` (doxycycline 100 mg capsules), `courses` (children's courses) and `amox500`
(amoxicillin 500 mg tablets). Every file with doses has a `label` (stock-planning figures, not
prescriptions); show it with them. Quezon City's and each barangay's people and units are
rounded to the nearest whole number. A health center's units are rounded up, the level stock is
ordered at, so the 66 centers add up to a little more than the city's total.

## Design tokens

`src/styles/tokens.css` holds the Figma file's variables and text styles (Foundations page),
under the names Figma's code syntax gives them. Use them for every color, corner and gap; never
write a hex color or a one-off radius or gap anywhere else.

| Kind | Use | Values |
| --- | --- | --- |
| Colors (30) | `var(--color-bg-canvas)`, `var(--color-text-primary)`, `var(--color-data-ramp-3)` | The Theme collection, Clinic mode |
| Corners | `var(--radius-xs)` badges, `-sm` tabs and fields, `-md` buttons, `-lg` cards and panels | 2, 4, 6, 8 px |
| Spacing | `var(--space-1)` to `var(--space-9)` | 4, 8, 12, 16, 24, 32, 48, 64, 96 px |
| Text (15) | `className="heading-m"`, `"body-m"`, `"data-xl"`, ... (Figma's Heading/M is `.heading-m`) | Figtree 400, 500, 600 |

Clinic (light) is the app's theme. The dark themes, Monsoon and Ember, are in the file too, for
a later theme switch: `<html data-theme="monsoon">`. If the design changes, change Figma first,
then `tokens.css`, keeping the names.

F11 darkened three Clinic colors so that all text meets WCAG AA (4.5:1) on bg/canvas, surface,
raised and inset: `text/tertiary` #626871 (was #8a9099), `status/warn` #905f18 (#b7791f) and
`status/alert` #ba3e2b (#c2412d). Figma's Theme collection must hold the same values in its
Clinic mode. A new color for text needs the same test against every surface it sits on.

Every CSS file ends up in one stylesheet that applies on every page, so two files that use the
same class name change each other's screens without any error. Start each class with its
file's name: `.home-hero` in `Home.css`, `.button-primary` in `Button.css`.

## Maps

Import MapLibre from `src/lib/maplibre.ts`, not from `'maplibre-gl'`:

```ts
import maplibregl from '../lib/maplibre.ts'
```

It hands MapLibre the address of its web worker, which Vite would otherwise leave out of the
build (every GeoJSON layer would fail with "Worker failed to load"). MapLibre 6 has no default
export of its own, so `import maplibregl from 'maplibre-gl'` from older tutorials fails.
React runs each effect twice in development (`StrictMode`), so create the map in a `useEffect`
and call `map.remove()` in its cleanup.

MapLibre adds about 1 MB of JavaScript. Import it only in the map screens, and load the `/map`
routes with React Router's `lazy` in `router.tsx`, so Home and the phone guide do not
download it. (`npm run build` warns that the map's chunk is over 500 kB: that is MapLibre.)

### The decluttered map (F18)

Reworked on 24 October 2026 from the team's review; the layout is the Figma section "Map ·
decluttered (proposal, 24 Oct)", frames D1 to D8, and its notes.

- **The logo and search never move.** They stay in the top left corner at every level. The city
  panel is a card under them (`--map-top-row`, `MapLayout.css`), 30% of the screen wide (400 to
  480 px, `map/motion.ts`) and as tall as the map leaves; it is the same size in both of its
  views, so switching never changes its length. On a phone it is a sheet from the bottom, as
  before.
- **Two tabs on the panel's edge** (`map/EdgeTabs.tsx`): Cases forecast and Prophylaxis plan,
  icons with no words, like bookmarks at the top of the card's right edge (on a phone, on the
  sheet's top edge). A tab's name shows on hover and is its aria-label. Compare models has left
  the panel; it is to move into How it works. Until then the site header's Results and its old
  addresses open How it works' Models part (`/how-it-works#models`), and `src/compare/` waits unused.
- **No Close button.** A click on empty map, outside Quezon City, closes the panel (CityMap's
  click handler), 300 ms later so a double click still zooms. A click on the city or a barangay
  does what it did, and a drag is no click.
  With a barangay's pop-up open, that click only closes the pop-up (`barangayLayers.ts`'s
  `selection()`). The open tab (its hover label is "Close"), Escape in the panel and the
  browser's Back close it too.
- **No "·" lines.** The panel's facts are label and value rows (`map/Facts.tsx`); the chart's
  ends are labelled "Last 15 weeks" and "Next week", and the threshold's count sits on its line.
  The subtitles under the city's name are gone.
- **The prophylaxis plan, less at once.** Forecast made (1, 2 or 3 days ahead) and the rain stay
  on top; under them one of three views: Summary (flagged, exposed, the stock needed), Barangays
  (the list, `map/MapList.tsx`, now always open inside the panel: each row's swatch is its color
  on the map) and Health centers (all of them, not the top four). Export stays at the bottom, with
  "Stock planning, not prescriptions." All storms and its list (`?storms=all`, `?from=`) are
  gone; a date without a plan says so.
- **What the words mean** (`map/WordHelp.tsx`): a ? at the panel's lower right opens plain
  definitions of the open view's words (90% range, epidemic threshold, Low, Watch, High; days
  ahead, exposed, flagged, each medicine, and DOH DM 2023-0309's doctor's consultation).
- **Methods behind the info button** (`map/MapInfo.tsx`): the info button under Zoom opens a
  pop-up with Methods (How it works), the data mode's sentence (it no longer sits under
  Simulation | Real data; screen readers still hear it change) and the sources' credits
  (MapLibre's attribution control, written out in full). The Methods link and the map's own "i"
  are gone from the corner.
- **No tutorial text.** The city tooltip's "Click to open the forecast" and the list's keyboard
  instructions are gone from the screen; the instructions stay for screen readers.

### Only the map (F14)

The app's map was reworked on 22 October 2026 at the team's request: after opening the map there
is only the map, of the whole country, with no other tabs.

- **The frame.** No app bar and no breadcrumb bar: the map fills the screen. Top left: the logo
  (home) and the search beside it (`map/MapSearch.tsx`). Top right: **Simulation | Real data**
  (`map/MapDataModes.tsx`); F18 moved the line saying what the mode shows into the info pop-up. Bottom middle: the timeline
  (`map/MapTimeline.tsx`): the date picker in the middle, between the previous and next week, and
  under it the week its forecast is for; under them a slider over every forecast week (the
  simulated ones amber), with each year marked under it. Bottom right: the legends and the map
  buttons, then **Methods** (How it works) and the sources' "i" (F18: both in the info button's pop-up). The hint
  ("Hover a city…") and the Cities list are gone; Quezon City's name on the map is the keyboard's
  way in.
- **Search.** The button beside the logo opens a field that finds any of the 1,642 cities and
  municipalities as the reader types (the phone guide's `matchPlaces`, `exposed/nearest.ts`),
  each with its province, since many towns share a name. The arrow keys move through the matches
  and Enter picks; Escape closes it. Quezon City opens its panel; any other town closes the panel,
  if open, and the camera flies to the town (`map/view.ts` `cityView`, CityMap's `found`), which
  keeps an outline of its own, `accent/primary` over a white casing, at every zoom: the "city-found"
  layers. The mark stays until the search finds another town, a city opens, or the pin button
  brings the Philippines back.
- **Lines come with the zoom** (`map/borders.ts`). The country's view has no lines at all: the
  land, the water and Quezon City's color. From zoom 6 (`ISLANDS_ZOOM`, a step in from the
  country's 5 on a laptop) the islands' coastlines (`ph_islands.json`) fade in with the street
  map's roads and rivers; from zoom 8 (`CITIES_ZOOM`) the towns' borders fade in as the coastlines
  fade out. Each fade takes 0.75 of a zoom level. The street map's own borders are left out at
  every zoom (`basemap.ts`). Below its zoom a layer is not drawn at all, so the country's view
  draws none of the 1,642 borders; and below `CITIES_ZOOM` the towns' see-through fills lose their
  smoothed edge (`fill-antialias`), which drew every border faintly where two fills met.
- **Closing the panel** (empty map, the open tab, Escape or the browser's Back since F18) steps the camera one zoom level out from
  where it is (`closeCamera`, `CLOSE_ZOOM_OUT`), so Quezon City stays in sight among its
  neighbours; the pin button shows the whole country.
- **The prophylaxis plan opens in 3D.** Opening the plan turns on the 3D view of its own accord
  (the Layers panel's switch shows it on): the camera tilts with the panel's slide, then circles
  Quezon City slowly, once in two minutes, easing in over 2 s (`map/orbit.ts`). The first click,
  touch, wheel or key on the map stops it for good, as do the zoom and pin buttons; the reader
  then turns the map by hand. Leaving the plan returns the map flat, unless the reader turned the
  3D switch on themselves (`?view=3d`). With reduced motion the plan opens tilted and does not
  circle.
- **The whole Philippines.** Level 1 shows all 1,642 cities and municipalities
  (`ph_cities.json`): thin outlines zoomed out, a light fill the street map shows through, and a
  tooltip with the town's province and "No data yet". Only Quezon City has data, colored by its
  outbreak level and named at every zoom, with next week's cases while it or its name is
  hovered; only it opens the panel.
- **The city panel** slides in from the left over about a third of the screen (36%, from 400 to
  560 px, `map/motion.ts`; half the screen, tried first, was too wide; a sheet from the bottom on
  a phone, as before), with three tabs: Cases forecast, **Compare models** (F9's
  chart, Controls and scores, on the mode's weeks) and Prophylaxis plan, and a Close button.
  F18 made it a card under the logo with two edge tabs and no Close button (above).
- **Simulation | Real data** (`?data=real`; Simulation is the default). QCESD's counts end on
  26 September 2026. Real data shows them and B10's forecasts only. Simulation adds
  `city_simulation.json`: the weeks since, each with a made-up count (the median of M4's
  forecast, so later forecasts see a typical week), and forecasts to next week, the last made
  with ECMWF's rain forecast of the day it ran (`src/app_simulation.py`). Every simulated number
  carries the amber "Simulated" badge, and simulated counts are dashed outlines in the charts.
  The scores are always the real run's. The prophylaxis plan has a plan for every date in both
  modes (F16, `src/app_days.py`): run `python -m src.app_days` on the day you run
  `python -m src.app_simulation`, so the daily plans reach its last date (check "F16 daily plans").
- **NOAH everywhere.** The flood zones cover every province NOAH has mapped
  (`noah_flood_<T>yr.pmtiles`, `src/noah_national.py`), read tile by tile through the `pmtiles`
  package; F13's Metro Manila overlays are gone.

### The map screens (F4, F5)

- **One map, three levels.** `MapLayout.tsx` holds the map (`map/CityMap.tsx`), its corners
  (F14, above) and the city panel. Each level's route fills the panel and names its level in
  `router.tsx` (`handle: { mapLevel: 2 }`). At level 1 the panel waits off-screen with Quezon
  City's forecast, as in Figma frame 1, so it slides in already filled.
- **Data.** The `/map` route's loader fetches `ph_cities.json`, `city_forecast.json` and (F14)
  `city_simulation.json` once, and (F13) the street map's style; a style that does not load in
  2 s leaves the map on its plain background, with all of LEPTON's data. In a level's component, `useMapContext()` (`map/mapContext.ts`) gives the files, the
  chosen date, that week's forecasts and the MapLibre map, for a level that draws its own
  layers (the map arrives once it has drawn the cities). It also gives two empty boxes for a
  level's own legend and tooltips, `legendSlot` beside the zoom buttons and `overlay` over the
  map, to fill with `createPortal` (F5 does).
- **Colors.** MapLibre paints on a canvas and cannot read CSS variables, so `CityMap` reads
  the token values once with `getComputedStyle`. The city with data is filled by its outbreak
  level: `levelOf()` in `map/forecast.ts` applies `city_forecast.json`'s `levels`, on the
  chance rounded as the panel shows it, so a "10%" never reads Low.
- **Motion.** The durations from the Figma notes are in `map/motion.ts`; `MapLayout` hands
  them to the CSS as variables. MapLibre does not animate a feature-state change, nor any
  paint value that differs from feature to feature. So animate a value the whole layer
  shares with a paint transition (the other cities' fade to 45%), or step a feature state
  each frame (`map/featureFades.ts`: `featureFader` for a hover, `stagger` for F5's wave).
- **Names on the map.** An HTML element that MapLibre keeps over the label point of the city
  with data (F2's `label_lon`, `label_lat`), so it is set in Figtree. The street map's own names
  (Noto Sans, from OpenFreeMap) name every other town, and leave out Quezon City, which LEPTON
  writes (`map/basemap.ts`); F14: at every zoom, so the one city with data stands out on the map
  of the whole country.
- **The street map (F13).** OpenFreeMap's Positron style under LEPTON's data, in the Figma map
  colors, with the cities' fills over its roads and under its names; zoomed out it shows the
  whole world, and the pin button above Zoom brings the open level back. The drawing order lives
  in `map/layerOrder.ts`; the sources' credits sit behind the "i" in the map's bottom left corner.
  The map is flat (Mercator), not a globe, and names appear without a fade (`fadeDuration: 0`):
  see "Keeping the map smooth" below.
- **The Layers panel (F13).** The Layers button above Zoom opens `map/MapLayers.tsx` (Figma
  "Layers panel"): it opens up from the button and covers the legends; on a phone it is a sheet
  like the city panel's. Escape or Close gives the keyboard back to the button. The base map is
  a group of radio buttons: Map (the street map), Satellite (Sentinel-2 cloudless 2024 by EOX,
  under the street map's roads and names) or Terrain (hill shading from Mapzen's Terrain Tiles),
  added on first use by `setBase` in `map/basemap.ts`. Over imagery or shading the city and
  barangay fills drop to 60% (terrain 75%, `DATA_OPACITY`). The choice lives in the address,
  `?base=satellite` or `?base=terrain` (`map/layerParams.ts`), and links between the levels keep it.
- **NOAH's flood zones (F13).** The panel's Flood hazard switch draws one of NOAH's maps
  (`map/floodLayer.ts`), the 25-year one first; while it is on, chips pick the 5-, 25- or
  100-year map, `?flood=25` in the address. F14: each map covers the whole country, a PMTiles
  file of vector tiles that MapLibre reads tile by tile (the `pmtiles` protocol). The zones go
  over LEPTON's fills and under the street map's names, in the `map/hazard-*` blues at 80%,
  and the cities' names get a halo. Their legend (`map/FloodLegend.tsx`) stands above the
  map's own; on a phone it shows only the levels' names (the depths are read out) and leaves
  the credit to the map's corner. While a file loads the panel says so; if it fails, the panel
  says that with a Try again button, and the legend goes. A failed map is removed, so choosing
  it later fetches it again. While a barangay's pop-up is open in the prophylaxis plan (opened
  from the list or by a click), only that barangay's zones are drawn, from its own small file
  (`noah_barangays/`), and the national tiles are hidden, so MapLibre fetches and draws none of
  them; the legend says "Only <barangay>'s zones". Closing the pop-up brings the whole map back.
- **The 3D view (F13).** The panel's "3D view" switch, `?view=3d` in the address
  (`map/terrain.ts`). The ground rises with Mapzen's Terrain Tiles (heights doubled: Metro
  Manila is low), the street map gets the hill shading, and its buildings stand up from zoom 14.
  The camera tilts 60°; the reader can turn and tilt it with a right-button drag, two fingers,
  or Shift and the arrow keys. Switching 3D off returns the map flat and facing north. F14: the
  prophylaxis plan turns it on by itself, and off when the plan closes (above).
- **Weather (F13).** The panel's Weather rows show one layer at a time, `?wx=` in the address
  (`map/weather.ts`): live clouds (Himawari-9 infrared, JMA, through NASA GIBS; the last 3 hours),
  live radar (RainViewer, the past 2 hours), live rain (NASA IMERG, the last 6 hours), and the
  map's date's rain (IMERG, one UTC day, 8 AM to 8 AM Philippine time) and satellite photo (NASA
  VIIRS). Each frame is a raster source and layer in the weather slot (`map/layerOrder.ts`), at
  opacity 0 but the one shown, so the animation does not flicker; frames are added newest first,
  one after another (RainViewer allows 100 requests a minute). GIBS can list a time before its
  tiles exist, and MapLibre draws a missing tile as nothing, so each GIBS frame is checked first
  with one headers-only request for its world tile. The live layers play 500 ms a frame, pausing on
  the newest, once every frame is in (not with reduced motion), and are fetched again every 10
  minutes; `map/WeatherTimeline.tsx` plays, pauses and steps them, with times in Philippine time
  and a badge saying they are now, not the map's date. `map/WeatherLegend.tsx` draws each layer's
  colors as its provider does (GIBS's colormaps, RainViewer's Universal Blue), so they are not
  tokens. A failed source says so in the panel, with Try again; a date NASA has no picture of
  says that.
- **The address (F13).** Every map layer is a setting in the address, left out at its default,
  so a link opens the same map and the links between the levels keep it (`map/layerParams.ts`):
  `?base=satellite|terrain`, `?flood=5|25|100`, `?view=3d`,
  `?wx=clouds|radar|rain|rain-day|photo-day`. For example
  `/map/quezon-city?date=2024-07-24&base=satellite&flood=25&wx=rain-day&view=3d` opens Quezon City
  on the day of Typhoon Carina, over imagery, in 3D, with NOAH's 25-year zones and that day's rain.
- **Privacy (F13).** The map now loads tiles from other servers: OpenFreeMap (always, unless it
  is blocked), and EOX, AWS, NASA GIBS and RainViewer when their layers are chosen. Each sees
  the reader's IP address and which part of the world is in view, as any web map's tile server
  does; none gets a cookie or anything LEPTON knows. The Exposure guide (F8) and Home's maps are
  SVG drawn from LEPTON's own files and load none of them.
- **The camera and the levels (F13).** A level's view (`map/view.ts`) is reached with
  `moveToLevel` (`levelCamera` and `easeTo`), not `fitBounds`: the zoom is the flat map's fit,
  and the level's padding (the panel, the sheet) becomes the camera's own, so the camera tilts,
  turns and zooms about the middle of the map left in sight. `fitBounds` shifts the middle only
  for a flat map, and on a phone a tilt threw the city off the strip above the sheet. Moves to a
  level's view carry `LEVEL_FIT`. The reader's own moves (a drag, a pinch, a key, the wheel, the
  zoom buttons with `READER_MOVE`) mark the map as moved: then a resize no longer refits the
  level, and 3D tilts where the reader is. MapLibre's own moves (a resize) mark nothing.
- **Keeping the map smooth (F13).** The map's lag was freezes, not slow frames. MapLibre
  compiles a WebGL shader the first time it draws each kind of layer, and on an integrated GPU
  each compile holds the page for 0.1 to 0.35 s. The street map brought many kinds of layer, and a
  globe compiles each shader twice (round, then flat as you zoom in). Measured on 22 October 2026
  (AMD Radeon integrated, headless Edge, panning and zooming each level):

  | | shaders at levels 1 / 2 / 3 | page frozen compiling | worst frame |
  | --- | --- | --- | --- |
  | before F13 | 6 / 7 / 10 | 0.15 to 0.28 s | 17 ms |
  | F13 with the globe | 13 / 25 / 31 | 0.75 to 1.57 s | 83 to 483 ms |
  | F13 flat, no label fade | 12 / 12 / 10 | 0.08 to 0.41 s | 17 ms |

  So the map is flat (Mercator) at every zoom, and names appear without a fade
  (`fadeDuration: 0`), which also stops MapLibre redrawing for 300 ms after every change of
  which names fit. Every layer but 3D now keeps a steady 60 frames a second; 3D runs at about
  55. Before adding a layer, mind what it costs: a new layer type (fill-extrusion, hillshade,
  heatmap), a dashed or patterned line, or a paint property that varies by feature where others
  are constant each mean another shader. The browser keeps compiled shaders while the tab is
  open, so each one freezes the page once.

  F14, measured 23 October 2026 (headless Edge on the GPU, 1440 × 900): zooming from the
  whole country to Metro Manila and back, through the coastlines and the towns' borders, ran at
  60 frames a second with no frame over 17 ms. The plan opened cold in 3D holds the page for up
  to 0.8 s at a time over its first 3.6 s (the terrain's first tiles and shaders), then circles at
  a steady 60. The circling never jumps ahead after such a pause (`LONGEST_STEP_MS`).

### The prophylaxis plan (F5)

Level 3, `/map/quezon-city/prophylaxis`, from Figma frames 3 and 3a. Stock planning, not
prescriptions: every dose on it sits under that label, in the panel, the tooltip and the
exported file.

- **Data.** The route's own loader (`map/planData.ts`) fetches `storms.json`, `centers.json`
  and `qc_barangays.geojson` the first time the plan opens. The forecast's barangay file is
  fetched when it is first shown, and kept; it must join the shapes on PSGC, all 142, or the
  page stops with an error.
- **Which forecast.** The date picks the storm. A storm's forecasts show from the day its
  earliest forecast was made (3 days ahead) to the last day of its rain or its flood
  (`stormDates` in `map/plan.ts`; Kristine: 18 to 24 October 2024). F16: every other date shows
  its own plan, for the 3 days of rain from that date (`days/<year>.json`, fetched when the date
  first reaches the year; "Loading the plan for this date…" until it comes): the forecasts made
  1 to 3 days before, or before February 2024, with no forecast archived, the rain that fell
  (no lead chips). Most days' plans are zero: "too little rain to flood: floods start above
  104 mm". (F18 removed "All storms", the list of storms that opened each at the first day of its
  1-day-ahead forecast's rain.) The lead chips keep the lead time
  in the address, `?lead=2` (1 day ahead without it). The numbers are for a 1-day flood with
  w = 0.5 (`PLAN_FLOOD`, as in Figma); C9's 7-day flood is there for the stretch switch.
- **Going back.** A link out of the plan (the Cases forecast tab, closing the panel) drops the
  plan's settings (`levelSearch` in `map/routes.ts`), so the plan opens afresh next time. (F18
  removed "All storms" and its visit, `?storms=all` and `?from=`.)
- **The barangays on the map** (`map/barangayLayers.ts`): a second source, drawn by three
  layers between Quezon City's fill and its outline (`map/cityLayers.ts`). Opening the plan,
  the lines fade in (300 ms), then the fills rise in a wave from the largest share of
  residents exposed to the smallest (600 ms) while the city's fill fades out and the other
  cities' outlines lighten, as in frame 3. Back plays it in reverse; another forecast or
  storm recolors the barangays in the same wave. The notes' "about 20 ms apart" cannot fit
  142 barangays into 600 ms (that takes 2.8 s), so the starts are spread over the 600 ms and
  each fill rises in 150 ms (`map/motion.ts`). The layers outlive the route's component, so
  Back can play before they are removed: `barangayLayers(map)` is the same object each time.
- **Panel, legend, tooltip** (`map/PlanPanel.tsx`, `ExposureLegend.tsx`,
  `BarangayTooltip.tsx`). The panel's health centers are frame 3's own rows (doxycycline and
  courses), not the three-column `CenterRow`, and their names drop "Health Center"
  (`centerName`). The tooltip adds the not-prescriptions badge, which 3a lacks (U2).
- **Export stock list** saves `lepton-stock-list_<storm>_lead<n>.csv`, made in the browser
  (`stockList`): the label, the forecast, the 66 health centers that get stock (the largest
  doxycycline need first), their sum, Quezon City's totals as on the panel, and the centers C7
  leaves out, with why. A center's units are rounded up, as F2 and D7 round them, so the 66
  add up to 29 to 37 units more than the city in each pool; the file says so.

### The barangay pop-up and report (F15)

Added on 24 October 2026 at the team's request: every barangay of the prophylaxis plan can be
clicked, and its pop-up makes a PDF report for its health office or LGU. Stock planning, not
prescriptions: the pop-up and every page of the report carry the label.

- **The pop-up** (`map/BarangayPopup.tsx`). A click or a tap on a barangay (`barangayLayers`'
  `onPick`), or Enter on a row of the barangay list (F11; F18: the panel's Barangays view), opens it where the barangay
  was clicked, or near its middle from the list. It shows what the tooltip shows
  (`BarangayNumbers` in `BarangayTooltip.tsx`, so the two never differ), a close button and
  **Generate Report**. It follows its point as the map moves (a drag, a zoom, the plan's
  circling), kept beside the city panel or above the phone's sheet as the tooltip is
  (`placeTooltip`, `panelCover`), and its barangay keeps the dark outline (feature state
  `selected`); the hover tooltip waits while it is open. A click on another barangay moves it
  there; a click on the map outside the barangays, its close button or Escape closes it. Opened
  from the list it takes the keyboard (Tab reaches Close, then Generate Report), and closing it
  gives the keyboard back to the list. On a date without a storm it says so and offers no report.
- **The report** (`src/report/`). Generate Report saves
  `lepton-barangay-report_<barangay>_<storm>_lead<n>.pdf`, made in the browser with jsPDF, as the
  stock list's CSV is: nothing is sent anywhere. A4, for the forecast on the map, written for the
  health centers and barangay health stations that hold the stock. Three pages:
  1. A cover: the LEPTON logo, the barangay and its 2024 residents, the storm, when the forecast
     was made and its rain, the health centers it is prepared for, and a QR code (with the link
     under it) that opens this forecast on the map.
  2. What to stock and where: residents exposed and whether the barangay is flagged, a card per
     unit for the map's 1-day flood (the line under the cards says whether those counts also
     cover the 7-day flood), the health centers that hold the stock (each with its share and its
     whole order, and the other barangays it supplies), and the barangay on a map of its
     neighbours with its centers pinned; the map fills what the page leaves.
  3. Details: who gets what (units per person, a column per flood), five plain points about the
     numbers, and the sources with their licences.

  It leaves out what a health center cannot act on: the PSGC, the barangay's rank among the 142,
  the storm's earlier forecasts, Quezon City's case forecast and the rain method in mm.
  `reportContent.ts` writes the words and tables, `reportPdf.ts` draws them, `reportMap.ts`
  holds the maps' geometry.
- **Its numbers** are the files', written out as the map writes them; only the units per person
  its text explains (from `counting`), and whether the 1-day counts cover the 7-day flood, are
  worked out in the browser. Two fields were added to F2's files for it:
  `centers.json`'s `barangay_centers` and `storms.json`'s `counting` (the Data table above).
  Check "F2 app data" compares both with a fresh export.
- **Logo and QR code.** The logo is `src/assets/logo/wordmark-1024.png`, built into the report's
  code (`?inline`). The QR code is drawn as squares (`qrcode-generator`, error correction M), so
  it prints sharp; it and the link under it are links in the PDF too.
- **Loading.** The report's code with jsPDF, the QR code and the logo is about 470 kB (170 kB
  compressed). The plan fetches
  it, with the storm's other forecasts, when a pop-up first opens, so the map carries none of it
  and the PDF is ready by the time the button is pressed. jsPDF's optional parts (html2canvas,
  DOMPurify, canvg) are built as files of their own that nothing loads.
- **Text and colors.** The PDF's font is Helvetica, a PDF's own: it prints the ñ in Doña Imelda
  and Santo Niño, but only Latin-1 and Windows-1252. Any other character (≥, →) stops the report
  with an error naming it, where jsPDF would print the line garbled. Colors are the Clinic
  tokens, read from the page and written out as #rrggbb by a canvas, since the built stylesheet
  shortens some (#ffffff to #fff).
- **Checked** (October 24, on `npm run preview` in a scripted Edge, at 1440 × 900 and on a
  390 × 844 phone, reduced motion on and off). Tatalon, Kristine 1 day ahead: the pop-up equals
  the tooltip and the files (36,809 of 58,286 exposed, 63%; 138,400, 13,463, 1,680), and so does
  the report, worked out by hand (7-day flood 46,133 capsules; Tatalon Health Center's whole
  need 170,644, 16,058, 2,063). Every way of opening and closing it, the keyboard path, a tap on
  the phone, the lead chips and the plan's circling; axe finds nothing in the pop-up; no console
  error. The three-page report (October 24) was drawn from the files in Node for six barangays:
  Tatalon, Payatas (4 centers), Claro (no center of its own), Santo Domingo (a long name),
  Doña Imelda (a center left out) and Tatalon on a forecast that floods nobody; each fits three
  pages.

## Home (F6)

The route `/`, from the Figma frame "Home" (node 19:256) and its notes. It draws F2's files and
its photos, and never loads MapLibre. Stock planning, not prescriptions: every dose on it sits
under that label.

- **Data.** The plan's preview and the stock figures are Kristine's forecast 1 day ahead
  (`PREVIEW_STORM` and `PREVIEW_LEAD` in `home/homeData.ts`, as the Home notes ask):
  `storms.json`, `centers.json`, the barangay shapes and `barangays/kristine_2024_lead1.json`,
  through F5's loaders, so opening the plan afterwards fetches nothing again. The preview's map
  is SVG drawn from `qc_barangays.geojson`, not MapLibre and not a picture: each barangay filled
  by its class, the flagged outlined in teal and the barangay of the list's first health center
  in black (Figma's "Selected"). The chart is the latest 36 weeks of `city_forecast.json`: each
  week's count, M4's forecast with its 90% range, and that week's threshold, under "Simulated
  until QCESD data" while the file says simulated. A file that cannot load leaves its section
  saying so; the rest of the page stands.
- **Photos.** Figma's four AI images are replaced by real photos from Wikimedia Commons under
  Creative Commons licences, each credited in the footer (`home/photos.ts`, check U8): the
  hero, Pasig City after Typhoon Ondoy (AusAID, CC BY 2.0); Quiapo in the July 2024 Carina
  floods (Michael Peronce, CC BY-SA 4.0); Damayang Lagi, Quezon City, after a downpour in 2023
  (LMP 2001, CC BY-SA 4.0); and the mud after Ondoy (AusAID, CC BY 2.0). The files in
  `src/assets/home/` are WebP at the Design notes' sizes: the hero 2880 × 1360 and 1440 × 680,
  the others 4:3 at 1200 × 900 and 800 × 600. To change a photo, make it at those sizes and
  change its entry in `photos.ts`, credit and all; a teammate's own photo is credited to them.
- **Words that differ from Figma**, which predates the results: the second photo's caption says
  heavy rain, not a typhoon (that flood came from a downpour); Try LEPTON says "The latest
  forecast, or any week since 2018", not "Today's forecast, or any day since February 2024"
  (LEPTON is not live); the badge is the app's "Simulated until QCESD data"; and the caption
  credits the boundaries the app draws (A5's: PSA and NAMRIA, via OCHA on HDX), not
  faeldon's. The numbers are today's files' (Tatalon 170,644 capsules; Figma shows an older
  export's 170,643).
- **Screens.** At 1440 px it matches the frame; wider, the content stays 1248 px wide in the
  middle. Below 1024 px every section is one column and the site header's links wrap under the
  logo; below 600 px the large text steps down to the next text style's size. No width scrolls
  sideways.

## The Leptospirosis page (F7)

`/leptospirosis`, from Figma frame "Leptospirosis" (38:277) and its notes, for residents.
Text only; no data files.

- **Sources.** Every medical fact ends with numbered links, `[1]`, to the Sources list at the
  bottom, each a DOH page (DM 2023-0309, DOH's disease page and two 2024 press releases) or,
  for the waterproof bandage, PIA. They are in
  `SOURCES` at the top of `Leptospirosis.tsx`; a new fact cites one with `<Cite sources={[...]} />`.
- **Text that differs from Figma**, so each fact matches its source: incubation 2 to 30 days, usually 1 to 2 weeks; "infected animals, especially
  rats"; high risk is DM 2023-0309's repeated or continuous exposure, not LEPTON's 2-day
  cut-off; "a doctor decides" on preventive medicine, as the memo requires a physician.
- **No hero photo yet.** Figma's is AI-generated (check U7). When a licensed photo arrives,
  set `HERO_PHOTO` (file, alt text, credit) and the photo and its credit appear.
- The page never gives doses. Before launch a health professional reviews the wording (Figma
  notes), and a teammate checks each fact against its source (F7's Done when).

## The exposure guide (F8)

The route `/exposed`, from Figma's three phone frames (39:301, 39:361, 39:411) and the guide's
notes beside them (40:356). It never names a medicine or a dose: a doctor or nurse decides.

- **Steps.** 1, Exposure check: five questions, each a group of radio buttons drawn as Figma's
  answer chips. 2, Your result: the risk group and what to do (`exposed/risk.ts`), with the
  emergency box on every result. 3, Nearest health centers: a map and the three nearest health
  centers. The step is in the address (`/exposed?step=2`), so the phone's Back goes back a step.
- **The rule** (`riskLevel`), from the notes: in floodwater more than once or for 2 days or more
  is high risk; otherwise a cut or wound, or floodwater in the eyes, nose or mouth, is moderate;
  otherwise low. Fever, muscle pain or red eyes now put "See a doctor today" first. "Not sure"
  about the eyes, nose or mouth counts as yes (assumption). Figma words only the moderate
  result; the others follow its pattern and DOH's advice (sources at the top of `risk.ts`). A
  health professional should review the words before launch, as F7 asks for its page.
- **Answers and location never leave the phone.** They live only in the screen's memory:
  nothing stores them, no request carries them, and a reload or leaving the guide forgets them
  (a reloaded `?step=2` opens step 1). Step 3 fetches only `centers.json` and
  `qc_barangays.geojson`, which hold nothing about the reader.
- **Location** is asked for only when the reader taps "Find the nearest health center".
  Browsers share it only with https pages and localhost, so test it on a phone with a Vercel
  preview link, not over the local network. If the reader says no, or the phone cannot tell,
  the reader types their barangay (`BarangayPicker.tsx`: accents, dots and "Sto." do not
  matter) and the distances start from a point inside it, near its middle (`middlePoint`).
  "Change" picks another barangay.
- **Distances** (`exposed/nearest.ts`) are straight lines (haversine) to the 66 health centers
  C7 sends stock to: the registry's second Bago Bantay entry has no coordinates (its first
  entry is listed) and Villamor Barangay Health Station's point lies 11 km from its barangay, so
  neither is offered. Each center's arrow, and the footer's button, open Google Maps with
  directions; the link holds only the center's coordinates, and Maps finds the start itself.
  No opening hours: Figma's are samples, shown only once the QC Health Department confirms them.
- **The map** (`GuideMap.tsx`) is SVG drawn from `qc_barangays.geojson`, so the guide never
  loads MapLibre: the barangays around the reader, the reader's barangay outlined, a teal square
  where the reader is, and the centers numbered as in the list. Figma shades the barangays by
  Kristine's forecast, as every map in the file does; the guide is not about a storm, so they
  are plain.
- **Done when** (app plan): it works on a real phone with location allowed and denied, and two
  known addresses give the same nearest centers and distances as a map's measuring tool. The
  list shows 0.1 km steps; haversine and a map's tool differ by a few metres across the city.

## Compare models (F9)

The route `/compare`, from Figma's frame "Compare models" (12:966) and its notes (34:365). The
frame draws the app bar and the Controls panel and leaves the room beside them empty; the
chart there is the one drawn for this page in How it works ("Weekly leptospirosis cases, Quezon
City · 2024", node 12:1010), and the scores under it follow How it works' models table (12:1482).

- **Data.** The route's own loader (`compare/compareData.ts`) fetches `city_forecast.json` and
  `storms.json`, and `scores.json` only when `city_forecast.json` says the run is real: F2
  writes it beside B10's real run only, and one from another B10 file than the forecasts' is
  not shown. The route loads only when opened (`lazy`), so Home does not download the chart.
- **Simulated.** While `city_forecast.json` says simulated, the chart, its tooltip and the
  latest week carry the amber "Simulated until QCESD data" badge, and every score and the
  primary result show "—", as the Figma notes ask: nothing on the page reads as a real result.
- **Controls** (`compare/ControlsPanel.tsx`). The five models' Toggle rows in their chart
  colors (`compare/models.ts`: M4 teal, M3 blue, the others grey); M4 and M3 start on, as in
  Figma. A Toggle row given a color keeps it when off, as in the frame. The Show rows (M4's 90%
  range, the epidemic threshold, the counts) carry their marks' colors; Figma leaves them teal.
  Figma's "Upload weekly cases" button is left out (it needs a server; the app plan cuts it),
  so the box under the controls names the latest week only.
- **Periods.** The latest 12 weeks, one year, or 2018–2026, kept in the address: `?period=12w`,
  `?period=2024`, `?period=all`; without one, the latest year. Figma's middle tab names one
  year (2024); the Year field under the tabs picks which. A year's axis spans all its 52 or 53
  MMWR weeks, so each year's season sits in the same place. The city panel's Compare models
  button (F4) opens the year of the week it shows.
- **The chart** (`compare/CompareChart.tsx`), drawn at the card's width so its labels stay
  12 px: each week's count as a grey bar, each model's forecast for the week (made the week
  before) as a line, M4's range shaded and the threshold dashed amber, as How it works draws
  them. A storm's flood is a hairline at the week it began (A11's dates in `storms.json`); a
  name that would touch another is left out. The COVID years are shaded: forecast, not scored.
  The counts axis reaches the tallest count or forecast drawn, raised for a range end or a
  threshold by at most half again (`axisTop`); anything higher runs off the top and the
  caption says so (on the made-up counts, weeks 25 and 26 of 2019–2025 have thresholds over
  800). M0 and "M4 without flood index" are dashed: the dataviz palette check finds the three
  greys too close to tell apart by color alone.
- **Reading a week.** Pointing at the plot (or tapping it on a phone) picks the nearest week:
  a crosshair, a dot on each line and a tooltip with every series' number. From the keyboard,
  Tab to the plot, then the arrow keys, Home and End; a screen reader hears each week as one
  sentence. "Show the weeks as a table" under the chart lists the same numbers.
- **Scores** (`compare/ScoreTable.tsx`): the primary result, D5's mean of |error M4| −
  |error M3| with its 95% interval, as a Stat card; then each model's MAE, MASE, WIS, 90%
  coverage and Brier score over the windows `scores.json` names, with what each score means in
  plain words. The rows run in D8's order, LEPTON's tinted.
- **Done when** (app plan): after B10's real run, the table equals D8's `d8_fig2_mae.csv`.
  Check "F9 scores" in `python -m src.checks` compares `scores.json` with it (each model's MAE
  and the 8-week M4 vs M3 row); it skips until B10's real run, F2's export and D8's table are
  all on the computer.

## How it works (F10)

`/how-it-works`, from Figma frame "How it works" (12:1385) and its notes. Text only; no data
files.

- **The text** is in `src/howItWorks/content.ts`: the pipeline diagram's cards, the models
  table, the three tests, the limits and the references. The plan takes it from the paper
  (E4, E5, E7), which is not final yet, so it comes from Notes.md, lepton-plan.md, config.py
  and `results/`. Check every sentence against the paper's final text (F10's Done when).
- **Section tabs** jump to `#pipeline`, `#models`, `#testing`, `#limits` and `#sources` (the
  site header's Sources link opens the last), and the tab of the part being read is selected.
- **Formulas** sit behind "Show the formula" in the models table (M0, M1 with the threshold,
  M4), from lepton-plan.md B5, B7 and B8, in `src/howItWorks/formulas.tsx`; none is in the
  main text.
- **Not as Figma:** the pipeline section draws no numbers. Its stat cards, weekly chart and
  score table are the map's and Compare models' (F9), so it links to both. An input still
  awaited carries the amber badge; none is, since QCESD's counts arrived. The limits list every
  limit the plan and Notes.md state (Figma shows five), and Sources credits every data set, map,
  font and photo, QCESD's counts among them (check U8; F12 added the photos and QCESD).

## Motion, accessibility and small screens (F11)

Fixes across the app, from the app plan's F11. Figma has no frames for the keyboard list or for
the map on a phone; both use the existing components and tokens.

- **Motion.** Checked in the browser against the drill-down notes: hover 150 ms; opening a city,
  the camera, the other cities' fade, the panel and the hint and names all take 700 ms on the
  ease-in-out curve; the barangays' lines 300 ms, then the 600 ms wave; Back plays it in
  reverse. With reduced motion every one is a 150 ms crossfade and the camera jumps: MapLibre
  skips a camera move not marked `essential`, so never mark one.
- **Focus.** Every link, button and field shows the same ring, 2 px of `accent/secondary`
  (`global.css`). A control in a box that clips its edges draws it inside itself
  (`outline-offset: -2px`), as the zoom buttons and the map's canvas do.
- **The map from the keyboard** (`map/MapList.tsx`). The plan's list of barangays (level 3) was a
  Panel header in the map's top left corner that opened a list; F18 put it in the panel's
  Barangays view, always open, and Escape there closes the panel instead. (F14 removed
  F11's "Cities · 17" at level 1; Quezon City's name on the map is a link the keyboard reaches.) Tab reaches the list; the arrow keys, Home, End or a name's first
  letters move through it, and the row reached thickens and shows its tooltip as under the
  pointer. Enter opens Quezon City's forecast; Escape closes the list. The plan's rows run from
  the most exposed, as the wave does. When the level changes, the keyboard moves to the panel's
  heading, or back at Metro Manila to the list, since the link just used has gone.
- **Screen readers.** Each row of the lists says its numbers: a city's level and expected cases,
  a barangay's residents exposed and its three units (the list says they are stock planning).
  Each panel keeps one `aria-live` line in the page, so a new week, a new forecast, a date
  without one and the storm list are all read out.
- **Small screens.** Every route holds at 1440, 1024 and 390 px without sideways scroll. Below
  768 px the app bar takes two rows and the map's breadcrumb bar keeps Back and the date picker.
  Below 600 px (`SHEET_BELOW` in `map/motion.ts`) the city panel is a sheet over the map's lower
  55% (`SHEET_SHARE`) that slides up from the bottom; the camera keeps the open city clear of it
  and of the legend standing on it (`panelCover`). An open list there hides the legend and shows
  no tooltip, which would cover its rows. On a touch screen the map's hint says tap, not hover.
- **Checked** (October 21, on `npm run preview`): Lighthouse accessibility 100 on all eight
  routes, desktop and mobile; axe finds nothing with the lists open; the map flow done from the
  keyboard alone, with reduced motion on, at 1440 and 390 px, in a scripted browser. F11's Done
  when still asks one teammate to do that flow by hand.

## Motion across the site (F17)

Added on 24 October 2026 at the team's request: every screen but the map stood still. The map's
own motion (F4, F5, F11, above) is unchanged; the rest of the site now moves with the same values.

- **Values.** CSS variables, for any new motion. Four are the map's own, set from
  `map/motion.ts` in `main.tsx` so the map and the rest of the site never drift apart:
  `--motion-hover` 150 ms for a control under the pointer (`HOVER_MS`), `--motion-enter` 700 ms for
  content arriving (`CAMERA_MS`), `--motion-crossfade` 150 ms (`CROSSFADE_MS`) and the ease-in-out
  `--motion-ease` (`EASE_CSS`). The site's own are in `src/styles/motion.css`: `--motion-change`
  300 ms for a value that changes in place (a switch's knob, a chart's bar, a chevron),
  `--motion-stagger` 80 ms between things that arrive together, and `--motion-ease-out` (fast,
  then slow) for what arrives.
- **Reduced motion.** As on the map: anything that moves sits inside
  `@media (prefers-reduced-motion: no-preference)`. With reduced motion, content appears with a
  150 ms crossfade (`--motion-crossfade`) and nothing slides, grows or turns. A change of color or
  opacity may stay outside the query.
- **Nothing moves on its own for long.** Each animation plays once, as its content arrives, or
  follows the reader (the pointer, the scroll). None loops, so no screen needs a pause button
  (WCAG 2.2.2); the longest, the guide's ripple, ends within 5 s.
- **Reveal on scroll** (`src/motion/reveal.ts`). Home, Leptospirosis and How it works call
  `useReveal()` on their `<main>`. Inside it, an element marked `data-reveal` waits hidden, 24 px
  low, until it first scrolls into view (above the screen's bottom 8%), then rises and fades in
  over 700 ms. Items of one list that arrive together start 80 ms apart; `--reveal-stagger` widens
  the gap and `--reveal-shift` changes where they come from (How it works' pipeline: 200 ms, from
  the left). A child can start its own animation once its block shows, with the selector
  `[data-revealed] .child` (Home's photos, preview and chart). Put `data-reveal` on a wrapper, not on
  a button: a component's own `transition` replaces the reveal's. Outside a screen that calls
  `useReveal()`, `data-reveal` does nothing and the element simply shows; on paper everything shows.
- **Counting up** (`src/motion/CountUp.tsx`). Home's three stock figures and the preview's two
  totals count up from 0 in 1.2 s the first time they scroll into view. Screen readers hear only
  the final number, and the page shows it before and after the count, so a printout, or a script
  reading the page, gets the files' numbers (check U1).
- **Home.** The hero's photo settles (from 108% over 2.4 s) and, where the browser has
  scroll-driven animations (not Firefox yet), falls behind the page as it scrolls. The headline
  rises line by line and the three waterlines come up from below, the lowest first. They are drawn
  in the page now (`home/waterlines.ts`, the same paths as the Figma export, which is gone), so each
  can move. The photos settle into their frames. The preview fills as the plan does on the map,
  with the map's timings (`LINES_MS`, `WAVE_MS`, `RISE_MS`): the outlines, a wave from the most
  exposed barangay to the least, then the flagged outlines, while the stock card slides in. The
  chart's weeks grow from the left as its lines draw across.
- **Controls.** Every button, tab, switch, chip, link and map control answers the pointer:
  Primary darkens, Secondary fills, a tab not selected takes a light tint, an arrow moves ahead (the
  download icon, down), a pressed button sinks to 97%, a switch's knob slides, a panel header's
  chevron turns, the header's links grow an underline and the logo's ripple turns a little. Hover
  styles sit inside `@media (hover: hover)`, so a tap on a phone leaves nothing stuck.
- **Pages.** Leptospirosis and How it works open with their first lines rising in turn, and their
  blocks rise in as they scroll into view. How it works' pipeline comes in step by step from the
  left, each arrow drawing toward its step, and "Show the formula" opens and closes smoothly where
  the browser can animate a height to `auto` (elsewhere it opens at once, as before). A click on a
  link to a place on the same page (the section tabs, the `[1]` links to the sources) glides there
  (`src/motion/smoothLinks.ts`); every other scroll, such as a new screen opening at its top, stays
  instant.
- **The guide.** A step slides in from the right going on and from the left going back (`move`,
  worked out in `Exposed.tsx`), and the progress bar's part fills, or empties going back. A chosen
  answer settles in with a small press; step 2's result, what to do and the emergency box arrive in
  turn; on step 3 the markers grow from their points after the map, the reader's square sends out
  three ripples, and the health centers come in nearest first.
- **The map.** A tab of the city panel fades in under the tabs, which stay; opening the city, the
  fade is over while the panel is still off-screen, so the panel still slides in filled. Another
  week slides the panel chart's bars and its chance bar to their new values, and a new level's badge
  fades to its colors. Compare models draws a new period's weeks from the left, and a model turned
  on fades in. The search grows out of its button; lists fade in.
- **Checked** (24 October, on `npm run preview` in a scripted Edge, at 1440 × 900 and on a
  390 × 844 phone): each animation midway and settled (Home's hero, reveals, wave, chart and
  counts; How it works' pipeline, tab glide and formula; the guide forward and back, location
  allowed; the map's week step, tab change, Compare's period and model switches); the numbers once
  counted (789,689 exposed, 3,174,170 capsules, 254,430 courses, 37,386 tablets); no sideways scroll
  on any route at 390 px; no console error. With reduced motion nothing moves on Home,
  Leptospirosis, How it works or the guide. U4 again: opening Quezon City, the panel slides in
  700 ms as before, its content faded in by 200 ms; with reduced motion, the 150 ms crossfade.

## Deploy and checks (F12)

F12 rebuilds the site from the latest results, puts it on Vercel (next section) and runs the
app plan's eight checks, U1 to U8, fixing every failure. After gate F (Thursday, October 22),
change only what a failed check needs.

- **Latest results.** On October 21, on `main` with B10's real run and F11 (`e4df763`),
  `python -m src.app_data` wrote the same 22 files that are committed; `python -m src.checks`
  passed "F2 app data" and "F9 scores"; `npm run build` and `npm run lint` passed.
- **The checks**, on `npm run preview` in a scripted Chrome, October 21:

| Check | How it was checked | Result |
| --- | --- | --- |
| U1 Numbers | F2's check, then each number on screen against F2's files: Kristine 1 day ahead (72 of 142 flagged, 789,689 exposed, 3,174,170 capsules, 254,430 courses, 37,386 tablets), each lead chip's own run, the top 4 health centers and the exported stock list (Quezon City's totals as on the panel); Tatalon's tooltip (36,809 of 58,286, 63%; 138,400, 13,463, 1,680); the city panel at the latest date and at 22 Oct 2024; Compare models' scores and primary result (−8.88, 95% interval −19.93 to −1.88); Home's preview and stock figures | Pass |
| U2 Labels | Every screen, the barangay list and tooltip, the exported stock list: each dose sits under "Stock planning, not prescriptions" | Pass. On B10's real run no "Simulated until QCESD data" badge is left |
| U3 Joins | F2's check: 17 of 17 cities, 142 of 142 barangays; 66 health centers get stock, and the 2 left out are listed with why | Pass |
| U4 Motion | Open Quezon City, Back from the plan, open the plan, comparing frames. Reduced motion off: frames still change midway and settle after the 700 ms camera and the 300 + 600 ms wave. On: the same frame from 350 ms, no camera move, the panel a 150 ms crossfade | Pass |
| U5 Access | Lighthouse: accessibility 100 on all eight routes, desktop and mobile (best practices and SEO 100 too). The map flow by keyboard only, reduced motion on: "Cities · 17", Quezon City, Prophylaxis plan, a lead chip, "Barangays · 142", Back, Back, with the focus ring at each step | Pass |
| U6 Screens | Every route at 1440, 1024 and 390 px: no sideways scroll, no console error; the guide's step 3 with location allowed and denied | Pass |
| U7 Nothing fake | The build searched for "sample", "placeholder" and "AI" (only MapLibre's own code matches); every button has a handler, and every link goes to a route, an anchor on its page or a live site | Failed on `/kit`: Figma's sample text and 8 buttons that do nothing. Fixed: the kit is in `npm run dev` only |
| U8 Credits | The footer and How it works' Sources | Failed: the footer credited only Home's photos, and Sources had neither the photos nor QCESD's counts. Fixed: the footer names every source of the data and fonts with its licence, and Sources lists the photos and QCESD |

- **Also for the deploy:** a favicon, the logo's O (`public/favicon.svg`: browsers asked for
  `/favicon.ico`, which does not exist), and `public/robots.txt` (without it `/robots.txt`
  answers with the page).
- **Still by hand**, by a teammate who did not build the screen: open the production link on two
  phones and two laptops (F12's Done when); the guide on two real phones, location allowed and
  denied (U6); the map flow by keyboard only with reduced motion on (U5, F11); the flow by eye
  with reduced motion off, then on (U4); and the six links whose sites refuse scripts, so only a
  person can open them (doh.gov.ph three times, pia.gov.ph, psa.gov.ph, openstat.psa.gov.ph).
  Then send the link to whoever writes E6 and E11.

## Deploy (Vercel)

The app is hosted on Vercel's free plan, built from this repository with `app/` as the root
directory. One-time setup, by the owner of the GitHub repository:

1. Sign in at vercel.com with GitHub.
2. Add New, then Project, then import `Project-Lepton`.
3. Set Root Directory to `app`. Vercel detects Vite: build command `npm run build`, output
   directory `dist`. Deploy.
4. Put the production link at the top of the repository's README (F12, for E10) and share it
   with the team.

After that, every push to `main` updates the production link, and every pull request gets its
own preview link. `vercel.json` sends every address except `/data/` and `/assets/` files to
`index.html`, so a link such as `/map/quezon-city` opens directly, while a data file that does
not exist answers 404, not with the page. `vite.config.ts` makes `npm run dev` and
`npm run preview` answer the same way, so `if (!res.ok)` after `fetch` is the test for a
missing file everywhere.
