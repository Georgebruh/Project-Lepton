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

A setting kept in the address's query (F4's forecast week) should change with
`setSearchParams(next, { preventScrollReset: true })`; otherwise the page jumps to the top.

## Components

`src/components/` holds the pieces every screen shares, built from the Figma Components page
(F3). Use them instead of drawing your own button or badge, so the screens stay alike. Open
http://localhost:5173/kit to see each one in every variant; choose Monsoon there to compare
them with the Figma page, which is drawn in that theme.

| Component | Use | Figma |
| --- | --- | --- |
| `Button` | `<Button variant="secondary" icon="arrow-right" to="/map">Try LEPTON</Button>`; `to` for a route, `href` for another site, `onClick` otherwise | Button, 3:65 |
| `Badge` | `<Badge tone="warn">Simulated until QCESD data</Badge>`; tones neutral, accent, warn, alert | Badge, 3:78 |
| `Tab` | `<Tab to="/map">Map</Tab>` is selected on its route; `<Tab selected onClick={...}>` otherwise | Tab, 3:83 |
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
| `ncr_cities.geojson` | NCR's 17 cities: `psgc`, `name`, `has_data` (Quezon City only) | Map |
| `qc_barangays.geojson` | Quezon City's 142 barangays: `psgc`, `name` | Map, Home |
| `storms.json` | Per storm and run (`observed`, `lead 1` to `lead 3`): `window`, `issued`, `rain_mm`, `position` against the return levels, `ei_pct`, `flagged`; per flood (`D1` is D = 1 at w = 0.5, `D7` is 7 days; the observed run has A11's D): `exposed` and the units. Also the five map `classes` | Prophylaxis plan |
| `barangays/<storm>_<run>.json` | Per barangay: `exposed`, `share`, `class` (0 to 4: `--color-data-ramp-1` to `-5`), `flagged`, `units` per flood | Prophylaxis plan, Home |
| `centers.json` | Health centers (`lat`, `lon`, `barangay`; `left_out` says why one gets no stock) and `needs[storm][run][flood][facility_code]` | Prophylaxis plan, Exposure guide |
| `city_forecast.json` | Per target week: `start`, `end`, `y`, `threshold`, `breached`, and per model `mu`, `low` and `high` (the 90% range), `p_breach`. `"simulated": true` until A13's counts arrive | Map, Compare models |
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
download it.

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
