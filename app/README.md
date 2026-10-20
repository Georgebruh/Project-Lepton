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
| `src/map/` | The map screens' parts (F4): the map, its legend, zoom buttons, breadcrumb bar, date picker and city panel; `routes.ts` names the three levels. F5's prophylaxis plan: the barangays on the map (`barangayLayers.ts`), its panel, legend and tooltip, and `plan.ts`, which reads its files |
| `src/home/` | Home's parts (F6): the plan's preview (`PlanPreview.tsx`), the city forecast's chart (`BacktestChart.tsx`), the photos and their credits (`photos.ts`) and the files it loads (`homeData.ts`) |
| `src/assets/` | Images the code imports; Vite gives each a hashed name under `/assets/` (F6: Home's photos and the hero's waterlines) |
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
shows the latest. Links between the map levels keep it (`MAP_PATHS[2] + search`).

## Components

`src/components/` holds the pieces every screen shares, built from the Figma Components page
(F3). Use them instead of drawing your own button or badge, so the screens stay alike. Open
http://localhost:5173/kit to see each one in every variant; choose Monsoon there to compare
them with the Figma page, which is drawn in that theme.

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
| `AppBar` | The header of the map screens and Compare models | Map frame, 55:319 |
| `Footer` | The footer, with the stock-planning note; `credits` adds the page's own credits under it (F6: Home's photos) | Home frame, 20:364 |
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
  for the helpline and the waterproof bandage, the QC government and PIA. They are in
  `SOURCES` at the top of `Leptospirosis.tsx`; a new fact cites one with `<Cite sources={[...]} />`.
- **Text that differs from Figma**, so each fact matches its source (the component's comment
  lists them): incubation 2 to 30 days, usually 1 to 2 weeks; "infected animals, especially
  rats"; high risk is DM 2023-0309's repeated or continuous exposure, not LEPTON's 2-day
  cut-off; "a doctor decides" on preventive medicine, as the memo requires a physician.
- **No hero photo yet.** Figma's is AI-generated (check U7). When a licensed photo arrives,
  set `HERO_PHOTO` (file, alt text, credit) and the photo and its credit appear.
- The page never gives doses. Before launch a health professional reviews the wording (Figma
  notes), and a teammate checks each fact against its source (F7's Done when).

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
  score table are the map's and Compare models' (F9), so it links to both. The Cases input
  carries the amber badge until QCESD's counts arrive. The limits list every limit the plan
  and Notes.md state (Figma shows five), and Sources credits every data set, map and font
  (check U8).

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
