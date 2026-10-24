import { createBrowserRouter } from 'react-router'
import App from './App.tsx'
import { loadMapData } from './map/mapData.ts'
import { loadPlanData } from './map/planData.ts'
import CompareRedirect from './screens/CompareRedirect.tsx'
import ErrorPage from './screens/ErrorPage.tsx'
import Exposed from './screens/Exposed.tsx'
import Home from './screens/Home.tsx'
import HowItWorks from './screens/HowItWorks.tsx'
import Leptospirosis from './screens/Leptospirosis.tsx'

/** The app's eight routes, one per screen in the file. */
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
            lazy: async () => ({ Component: (await import('./screens/MapPhilippines.tsx')).default }),
          },
          {
            path: 'quezon-city',
            handle: { mapLevel: 2 },
            lazy: async () => ({ Component: (await import('./screens/MapQuezonCity.tsx')).default }),
          },
          {
            path: 'quezon-city/compare',
            handle: { mapLevel: 2 },
            lazy: async () => {
              const [{ default: Component }, { loadCompareData }] = await Promise.all([
                import('./screens/MapCompare.tsx'),
                import('./compare/compareData.ts'),
              ])
              return { Component, loader: loadCompareData }
            },
            shouldRevalidate: () => false,
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
      { path: '/compare', element: <CompareRedirect /> },
      { path: '/how-it-works', element: <HowItWorks /> },
      ...DEV_ROUTES,
    ],
  },
])
