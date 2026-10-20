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
| `src/screens/` | One file per screen. Each is a placeholder until its task builds it |
| `src/components/` | The shared components (F3), shown together at `/kit` |
| `src/compare/` | Compare models' parts (F9): the chart (`CompareChart.tsx`), its tooltip, keys and table view, the Controls panel and the scores; `periods.ts` holds the three periods and the x axis, `models.ts` each model's name, color and line, `chartGeometry.ts` the chart's sizes and paths, `compareData.ts` the route's loader |
| `src/map/` | The map screens' parts (F4): the map, its legend, zoom buttons, breadcrumb bar, date picker and city panel; `routes.ts` names the three levels. F5's prophylaxis plan: the barangays on the map (`barangayLayers.ts`), its panel, legend and tooltip, and `plan.ts`, which reads its files |
| `src/styles/tokens.css` | Every color, corner radius, spacing step and text style, from Figma |
| `src/styles/global.css` | Page-wide base styles |
| `src/lib/maplibre.ts` | MapLibre, set up for Vite; map code imports it from here |
| `public/data/` | F2's data files, fetched as `/data/<file>` |
| `vercel.json` | Sends every screen's address to the app on Vercel |
| `vite.config.ts` | Vite's settings; a missing `/data/` file answers 404 here too, as on Vercel |

## Screens

The three map levels share `MapLayout.tsx`, so the one map stays on screen while the reader
drills down; each level's own content shows inside it. Figma node ids are in each file.

| Route | Screen | File | Task |
| --- | --- | --- | --- |
| `/` | Home | `Home.tsx` | F6 |
| `/map` | Map: Metro Manila | `MapMetroManila.tsx` | F4 |
| `/map/quezon-city` | Map: Quezon City's case forecast | `MapQuezonCity.tsx` | F4 |
| `/map/quezon-city/prophylaxis` | Map: prophylaxis plan | `MapProphylaxis.tsx` | F5 |
| `/leptospirosis` | Leptospirosis, for residents | `Leptospirosis.tsx` | F7 |
| `/exposed` | The "I have been exposed to floodwater" guide | `Exposed.tsx` | F8 |
| `/compare` | Compare models | `CompareModels.tsx` | F9 |
| `/how-it-works` | How it works | `HowItWorks.tsx` | F10 |

Any other address, and any error while drawing a screen, shows `ErrorPage.tsx`. When a screen
is built, it stops using `Placeholder.tsx`; delete that file (and `Placeholder.css`) when no
screen uses it.

A setting kept in the address's query should change with
`setSearchParams(next, { preventScrollReset: true })`; otherwise the page jumps to the top.
The map keeps its date there: `/map/quezon-city?date=2024-10-22` (F4). The date picks the
forecast day, the MMWR week holding it, and the panel shows the forecast made that week for
the week after ("next week"); without a date, or with one outside the backtest, the map
shows the latest. Links between the map levels keep it (`MAP_PATHS[2] + search`). Compare
models keeps its period there: `/compare?period=2024` (F9).

## Components

`src/components/` holds the pieces every screen shares, built from the Figma Components page
(F3). Use them instead of drawing your own button or badge, so the screens stay alike. Open
http://localhost:5173/kit to see each one in every variant; choose Monsoon there to compare
them with the Figma page, which is drawn in that theme.

| Component | Use | Figma |
| --- | --- | --- |
| `Button` | `<Button variant="secondary" icon="arrow-right" to="/map">Try LEPTON</Button>`; `to` for a route, `href` for another site, `onClick` otherwise | Button, 3:65 |
| `Badge` | `<Badge tone="warn">Simulated until QCESD data</Badge>`; tones neutral, accent, warn, alert | Badge, 3:78 |
| `Tab` | `<Tab to="/map">Map</Tab>` is selected on its route; `<Tab selected onClick={...}>` otherwise. With both, `selected` wins (F4's panel tabs) | Tab, 3:83 |
| `ToggleRow` | `<ToggleRow label="M3" on={on} onChange={setOn} color="var(--color-chart-m3)" />` | Toggle row, 3:94 |
| `StatCard` | `<StatCard label="Residents exposed" value="789,689" caption="..." />` | Stat card, 4:8 |
| `CenterRow` | One health center's doxycycline, children's courses and amoxicillin; rows go in a `role="table"` | Center row, 4:12 |
| `PanelHeader` | A side-panel section's title that opens and closes it | Panel header, 4:17 |
| `SiteHeader` | The header of Home, Leptospirosis and How it works | Site header, 4:21 |
| `AppBar` | The header of the map screens and Compare models | Map frame, 55:319 |
| `Footer` | The footer, with the stock-planning note | Home frame, 20:364 |
| `Logo` | The logo; the headers and the footer already include it | Logo, 3:47 |
| `Icon` | `<Icon name="calendar" size={16} />`, any of the 18 Figma icons, in the text color | icon/…, Components page |

Each component's CSS starts its classes with the component's name (`.button-primary` in
`Button.css`). In Figma, the 1 px border of the Secondary button and the Selected tab adds to
their size, so they are 2 px larger than the others (46 px tall, not 44); the CSS does the
same. A row of tabs therefore lines them up at the top (`align-items: flex-start`). The logo's
wordmark is Instrument Sans SemiBold, as in the Figma Logo; `index.html` loads only its six
letters. Every other text is Figtree.

## Data (F2)

`python -m src.app_data`, run from the repository root, writes the data files into
`public/data/`. The app fetches them as `/data/<file>` and computes nothing but map styling
and distances. Barangays and cities join on the 10-digit PSGC (`psgc`, a string). Rerun it
whenever C8, C9 or B10 change, then commit the files.

| File | What it holds | Screens |
| --- | --- | --- |
| `ncr_cities.geojson` | NCR's 17 cities: `psgc`, `name`, `has_data` (Quezon City only), and `label_lon`, `label_lat`, where the map writes the name (empty for Pateros, too small) | Map |
| `qc_barangays.geojson` | Quezon City's 142 barangays: `psgc`, `name` | Map, Home |
| `storms.json` | Per storm and run (`observed`, `lead 1` to `lead 3`): `window`, `issued`, `rain_mm`, `position` against the return levels, `ei_pct`, `flagged`; per flood (`D1` is D = 1 at w = 0.5, `D7` is 7 days; the observed run has A11's D): `exposed` and the units. Also the five map `classes` | Prophylaxis plan |
| `barangays/<storm>_<run>.json` | Per barangay: `exposed`, `share`, `class` (0 to 4: `--color-data-ramp-1` to `-5`), `flagged`, `units` per flood | Prophylaxis plan, Home |
| `centers.json` | Health centers (`lat`, `lon`, `barangay`; `left_out` says why one gets no stock) and `needs[storm][run][flood][facility_code]` | Prophylaxis plan, Exposure guide |
| `city_forecast.json` | Per target week: `start`, `end`, `y`, `threshold`, `breached`, and per model `mu`, `low` and `high` (the 90% range), `p_breach`. `"simulated": true` until A13's counts arrive. Also `map_model` (M4, the model the map shows) and the outbreak `levels`, each with the Pr(breach) it starts at (`config.APP_LEVELS`) | Map, Compare models |
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

### The map screens (F4, F5)

- **One map, three levels.** `MapLayout.tsx` holds the app bar, the breadcrumb bar with the
  date picker, the map (`map/CityMap.tsx`), its legend and zoom buttons, and the panel on the
  right. Each level's route fills the panel and names its level in `router.tsx`
  (`handle: { mapLevel: 2 }`). At level 1 the panel waits off-screen with Quezon City's
  forecast, as in Figma frame 1, so it slides in already filled.
- **Data.** The `/map` route's loader fetches `ncr_cities.geojson` and `city_forecast.json`
  once. In a level's component, `useMapContext()` (`map/mapContext.ts`) gives the files, the
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
- **Names on the map.** HTML elements that MapLibre keeps over each city's label point (F2's
  `label_lon`, `label_lat`), so they are set in Figtree: the blank map style has no font
  files for MapLibre's own text.

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
  (`stormDates` in `map/plan.ts`; Kristine: 18 to 24 October 2024). Any other date says "No
  storm forecast for this date" and links to each storm at the first day of its 1-day-ahead
  forecast's rain (Kristine: Tue 22 Oct 2024, Figma's date). The lead chips keep the lead time
  in the address, `?lead=2` (1 day ahead without it). The numbers are for a 1-day flood with
  w = 0.5 (`PLAN_FLOOD`, as in Figma); C9's 7-day flood is there for the stretch switch.
- **Going back.** While a storm is shown, "All storms" beside the heading (not in Figma) lists
  the storms again, at the same date (`?storms=all`). A storm opened from that list is a visit:
  the address keeps the date from before it (`?from=`), and a link out of the plan (Back, the
  trail, the Cases forecast tab) puts that date back and drops the plan's settings
  (`levelSearch` in `map/routes.ts`), so the plan opens afresh next time. The browser's Back
  button returns to the list too. Picking a date with the date picker ends the visit.
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

## Deploy (Vercel)

The app is hosted on Vercel's free plan, built from this repository with `app/` as the root
directory. One-time setup, by the owner of the GitHub repository:

1. Sign in at vercel.com with GitHub.
2. Add New, then Project, then import `Project-Lepton`.
3. Set Root Directory to `app`. Vercel detects Vite: build command `npm run build`, output
   directory `dist`. Deploy.
4. Share the production link with the team.

After that, every push to `main` updates the production link, and every pull request gets its
own preview link. `vercel.json` sends every address except `/data/` and `/assets/` files to
`index.html`, so a link such as `/map/quezon-city` opens directly, while a data file that does
not exist answers 404, not with the page. `vite.config.ts` makes `npm run dev` and
`npm run preview` answer the same way, so `if (!res.ok)` after `fetch` is the test for a
missing file everywhere.
