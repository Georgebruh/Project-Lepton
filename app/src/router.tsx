import { createBrowserRouter } from 'react-router'
import App from './App.tsx'
import CompareModels from './screens/CompareModels.tsx'
import ErrorPage from './screens/ErrorPage.tsx'
import Exposed from './screens/Exposed.tsx'
import Home from './screens/Home.tsx'
import HowItWorks from './screens/HowItWorks.tsx'
import Kit from './screens/Kit.tsx'
import Leptospirosis from './screens/Leptospirosis.tsx'
import MapLayout from './screens/MapLayout.tsx'
import MapMetroManila from './screens/MapMetroManila.tsx'
import MapProphylaxis from './screens/MapProphylaxis.tsx'
import MapQuezonCity from './screens/MapQuezonCity.tsx'

/**
 * F1: the app's eight routes, one per screen in the Figma file. The three map levels are
 * children of MapLayout, so the one map stays on screen while the reader drills down from
 * Metro Manila to Quezon City to its prophylaxis plan. Any other address, and any error while
 * drawing a screen, shows ErrorPage. F3 adds /kit, the component kit: not a screen, for
 * checking the shared components against Figma.
 */
export const router = createBrowserRouter([
  {
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/', element: <Home /> },
      {
        path: '/map',
        element: <MapLayout />,
        children: [
          { index: true, element: <MapMetroManila /> },
          { path: 'quezon-city', element: <MapQuezonCity /> },
          { path: 'quezon-city/prophylaxis', element: <MapProphylaxis /> },
        ],
      },
      { path: '/leptospirosis', element: <Leptospirosis /> },
      { path: '/exposed', element: <Exposed /> },
      { path: '/compare', element: <CompareModels /> },
      { path: '/how-it-works', element: <HowItWorks /> },
      { path: '/kit', element: <Kit /> },
    ],
  },
])
