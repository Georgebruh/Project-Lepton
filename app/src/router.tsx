import { createBrowserRouter } from 'react-router'
import App from './App.tsx'
import { loadMapData } from './map/mapData.ts'
import { loadPlanData } from './map/planData.ts'
import ErrorPage from './screens/ErrorPage.tsx'
import Exposed from './screens/Exposed.tsx'
import Home from './screens/Home.tsx'
import HowItWorks from './screens/HowItWorks.tsx'
import Leptospirosis from './screens/Leptospirosis.tsx'

/**
 * F1: the app's eight routes, one per screen in the Figma file. The three map levels are
 * children of MapLayout, so the one map stays on screen while the reader drills down from
 * Metro Manila to Quezon City to its prophylaxis plan. Any other address, and any error while
 * drawing a screen, shows ErrorPage. F3 adds /kit, the component kit: not a screen, for
 * checking the shared components against Figma.
 *
 * F4: the map routes load only when opened (`lazy`), so Home and the phone guide never
 * download MapLibre (about 1 MB). The /map route's loader fetches the map's files before the
 * map draws; shouldRevalidate keeps them when the address's date changes, since React Router
 * would otherwise fetch them again on any change to the query. Each level names its number
 * in its handle (map/routes.ts).
 *
 * F5: the prophylaxis plan's own loader fetches its files (storms, health centers, barangay
 * shapes) only when the plan first opens, and keeps them while the date and lead change.
 *
 * F6: Home previews the plan with the same files and loaders, so the two small modules that
 * fetch them (map/mapData.ts, map/planData.ts) are part of every page. Their loaders sit on the
 * map routes directly and fetch while the screen's code loads; the map's code, with MapLibre,
 * still loads only when the map opens.
 *
 * F9: Compare models loads only when opened (`lazy`), as the map does, so Home never downloads
 * its chart. Its loader fetches the city forecast, the storms and, beside a real run, the
 * scores, and keeps them while the period in the address changes.
 *
 * F12: /kit is in `npm run dev` only. Its Figma sample text and its buttons that do nothing
 * would fail check U7 (nothing fake ships), so the built site, the one Vercel serves, leaves it
 * out: there /kit shows ErrorPage, as any other unknown address does.
 */
const DEV_ROUTES = import.meta.env.DEV
  ? [{ path: '/kit', lazy: async () => ({ Component: (await import('./screens/Kit.tsx')).default }) }]
  : []

export const router = createBrowserRouter([
  {
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/', element: <Home /> },
      {
        path: '/map',
        loader: loadMapData,
        lazy: async () => ({ Component: (await import('./screens/MapLayout.tsx')).default }),
        shouldRevalidate: () => false,
        hydrateFallbackElement: <p className="route-loading body-m">Loading the map…</p>,
        children: [
          {
            index: true,
            handle: { mapLevel: 1 },
            lazy: async () => ({ Component: (await import('./screens/MapMetroManila.tsx')).default }),
          },
          {
            path: 'quezon-city',
            handle: { mapLevel: 2 },
            lazy: async () => ({ Component: (await import('./screens/MapQuezonCity.tsx')).default }),
          },
          {
            path: 'quezon-city/prophylaxis',
            handle: { mapLevel: 3 },
            loader: loadPlanData,
            lazy: async () => ({ Component: (await import('./screens/MapProphylaxis.tsx')).default }),
            shouldRevalidate: () => false,
          },
        ],
      },
      { path: '/leptospirosis', element: <Leptospirosis /> },
      { path: '/exposed', element: <Exposed /> },
      {
        path: '/compare',
        lazy: async () => {
          const [{ default: Component }, { loadCompareData }] = await Promise.all([
            import('./screens/CompareModels.tsx'),
            import('./compare/compareData.ts'),
          ])
          return { Component, loader: loadCompareData }
        },
        shouldRevalidate: () => false,
        hydrateFallbackElement: <p className="route-loading body-m">Loading the forecasts…</p>,
      },
      { path: '/how-it-works', element: <HowItWorks /> },
      ...DEV_ROUTES,
    ],
  },
])
