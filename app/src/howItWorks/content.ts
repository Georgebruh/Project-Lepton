/**
 * F10: the text of How it works, kept in one place. The plan takes it from the paper (E5's
 * Methodology in plain words, every limit E4 lists, E7's references); the paper is not final
 * yet, so this text comes from what the paper is written from: Notes.md, lepton-plan.md,
 * config.py and results/. When the paper is final, check every sentence here against it.
 */

import { HERO_PHOTO, STRIP_PHOTOS } from '../home/photos.ts'

/** One card in the pipeline diagram. */
export type PipelineCard = {
  /** The small label over the title, e.g. "Rain". */
  label: string
  title: string
  text: string
  /** Data we do not have yet: the card carries the amber "Simulated until QCESD data" badge. */
  awaited?: boolean
}

/** The diagram's four steps, left to right (Figma 12:1401). */
export const PIPELINE: { step: string; cards: PipelineCard[] }[] = [
  {
    step: '01 · Inputs',
    cards: [
      {
        label: 'Rain',
        title: 'NASA IMERG · ECMWF',
        text: 'Observed daily rain since June 2000; forecasts 1–3 days ahead via Open-Meteo',
      },
      { label: 'Flood hazard', title: 'Project NOAH maps', text: '5-, 25- and 100-year flood zones' },
      {
        label: 'People',
        title: 'WorldPop 100 m · PSA',
        text: '2024 population grid, 2020 census by age, 2024 births',
      },
      {
        label: 'Places',
        title: 'DOH facility registry',
        text: 'Health centers and barangay health stations',
      },
      {
        label: 'Cases',
        title: 'QCESD weekly counts',
        text: 'Cases by week of onset, 2015–2026, from QCESD’s case list; weekly totals only',
      },
    ],
  },
  {
    step: '02 · Shared computation',
    cards: [
      {
        label: 'Flood exposure index',
        title: 'Who does this storm flood?',
        text: '3-day catchment rain is placed against its return levels, then mapped to the share of each barangay’s residents in flooded zones.',
      },
    ],
  },
  {
    step: '03 · Two models',
    cards: [
      {
        label: 'Layer 1 · city',
        title: 'M4 · negative binomial',
        text: 'Season (Fourier terms), recent cases, two weeks of rain and the exposure index, with Quezon City’s population as an offset.',
      },
      {
        label: 'Layer 2 · barangay',
        title: 'Exposure × DOH regimens',
        text: 'Exposed adults by DM 2023-0309 risk tier, children and pregnant women, split to the nearest health centers.',
      },
    ],
  },
  {
    step: '04 · What the office gets',
    cards: [
      {
        label: 'Next week',
        title: 'Cases with a 90% range',
        text: 'Plus the probability of crossing the epidemic threshold (mean + 2 SD of the last 3–5 normal years).',
      },
      {
        label: 'Next 1–3 days',
        title: 'Units per health center',
        text: 'Doxycycline 100 mg, children’s courses and amoxicillin 500 mg. Stock planning, not prescriptions.',
      },
    ],
  },
]

/** Which formula a model row can show (formulas.tsx). */
export type FormulaId = 'm0' | 'm1' | 'm4'

/** The models table (Figma 12:1482), in Figma's order. */
export const MODELS: {
  name: string
  text: string
  /** A badge's tone and label, or plain text for "Baseline". */
  role: { tone?: 'neutral' | 'accent' | 'warn'; label: string }
  formula?: FormulaId
  /** LEPTON's own row, tinted. */
  ours?: boolean
}[] = [
  {
    name: 'M0 · Same week last year',
    text: 'The count exactly 52 weeks before the target week.',
    role: { label: 'Baseline' },
    formula: 'm0',
  },
  {
    name: 'M1 · Seasonal average',
    text: 'Mean of that week over the last 3–5 normal years — the threshold’s own average.',
    role: { label: 'Baseline' },
    formula: 'm1',
  },
  {
    name: 'M3 · Prophet + XGBoost',
    text: 'Latigay & Gonzaga (2026), re-implemented and refit every week on the weeks it may see.',
    role: { tone: 'neutral', label: 'Published benchmark' },
  },
  {
    name: 'M4 · LEPTON',
    text: 'Negative binomial on season, recent cases, rain and the flood exposure index.',
    role: { tone: 'accent', label: 'Ours' },
    formula: 'm4',
    ours: true,
  },
  {
    name: 'M4 without flood index',
    text: 'The same model with the exposure index removed.',
    role: { tone: 'warn', label: 'Tests the flood idea' },
  },
]

/** How we check it: three cards (Figma 12:1514). */
export const TESTS: { label: string; title: string; text: string }[] = [
  {
    label: 'Layer 1',
    title: 'Rolling-origin backtest',
    text: 'Every week from 2018 to 2026, each model is refit on only the weeks it could have seen, then forecasts the next week. A check overwrites future counts to prove nothing leaks.',
  },
  {
    label: 'Scores',
    title: 'Error, range and alarms',
    text: 'Mean absolute error is the primary endpoint, with a 95% moving-block bootstrap interval. Also the weighted interval score, Brier skill score and CORP reliability. Headline scores leave out 2020–2021.',
  },
  {
    label: 'Layer 2',
    title: 'Four real storms',
    text: 'Carina and Kristine (2024), the July 2025 floods and the August 2026 habagat — on observed rain and on forecasts made 1–3 days ahead, against flood reports.',
  },
]

/**
 * What LEPTON can't do yet. The Figma notes ask for every limit the paper states; these are
 * the plan's E4 list (corrections 2, 8 and 9 and the assumptions table) and Notes.md
 * sections 1 to 3, in plain words.
 */
export const LIMITS: { title: string; text: string }[] = [
  {
    title: 'Satellite rain under-reads typhoon peaks',
    text: 'IMERG puts Carina’s rain at the no-flood floor, so the observed run sizes almost no stock for it (Aryastana et al., 2022; Veloria et al., 2021).',
  },
  {
    title: 'Reanalysis rain misses the highest days too',
    text: 'ERA5, whose return levels judge the forecasts, also misses the highest daily totals (Lavers et al., 2022). It moves where a forecast falls, not the comparison’s fairness.',
  },
  {
    title: 'Final counts, not real-time ones',
    text: 'The backtest uses QCESD’s final counts by week of onset and hides the last 2 weeks at each forecast. Counts reported in real time arrive later, so real-time accuracy may be lower.',
  },
  {
    title: 'Benchmark only partly reproduced',
    text: 'Our M3 matches the published Prophet error within 5%, but its hybrid error is 24.60, not 16.72. M4 is compared with our M3.',
  },
  {
    title: 'No barangay case counts',
    text: 'Layer 2 is checked against flood reports, so it is a demonstration, not a validation. The reports name only some flooded barangays.',
  },
  {
    title: 'Untuned flood floor',
    text: 'R0 = 0.5 × R(5) is a stated starting value; tuning it needs DRRMO-listed floods.',
  },
  {
    title: 'Flood maps give no storm length',
    text: 'NOAH’s maps do not state their design rain duration, so neither a 1- nor a 3-day total can be tied to them. LEPTON uses 3-day totals.',
  },
  {
    title: 'Rare storms are uncertain',
    text: 'With about 25 years of satellite rain, the 25-year storm’s rain is uncertain by roughly ±15%, which moves where a storm falls between the maps.',
  },
  {
    title: 'Contact assumptions',
    text: 'Everyone in a flooded zone is counted as touching the water, at any depth. Offices scale by their own coverage.',
  },
  {
    title: 'Wounds and flood length unknown',
    text: 'Who had a wound or swallowed water is unknown, so short floods are reported at three shares. Forecasts cannot know the flood’s length, so they show 1 and 7 days.',
  },
  {
    title: 'Groups the census cannot count',
    text: 'Pregnant women are estimated from births × 0.75 and ages from the 2020 census. Lactating women are not separated: DM 2023-0309 gives them no regimen.',
  },
  {
    title: 'A chosen flag line',
    text: 'A barangay is flagged when 25% or more of its residents live in zones the rain floods. The team chose this line and also reports 50%.',
  },
  {
    title: 'One city',
    text: 'Quezon City only, for now. Each other city needs its own weekly case counts.',
  },
]

/** The plan's cut items, named under the list as future work. */
export const FUTURE_WORK =
  'Left for future work: Cebu City, live weekly forecasts, nowcasting from report dates, a distributed-lag model, a satellite flood check (Sentinel-1) and hospital demand.'

/** One reference: its text (APA 7 style) and a link to it; no link for data shared on request. */
export type Reference = { text: string; url?: string }

/** Papers and guidelines behind each choice, alphabetical. */
export const PAPERS: Reference[] = [
  {
    text: 'Abon, C. C., David, C. P. C., & Pellejera, N. E. B. (2011). Reconstructing the Tropical Storm Ketsana flood event in Marikina River, Philippines. Hydrology and Earth System Sciences, 15(4), 1283–1289.',
    url: 'https://doi.org/10.5194/hess-15-1283-2011',
  },
  {
    text: 'Aryastana, P., Liu, C.-Y., Jou, B. J.-D., Cayanan, E., Punay, J. P., & Chen, Y.-N. (2022). Assessment of satellite precipitation data sets for high variability and rapid evolution of typhoon precipitation events in the Philippines. Earth and Space Science, 9(9), e2022EA002382.',
    url: 'https://doi.org/10.1029/2022EA002382',
  },
  {
    text: 'Bagtasa, G. (2022). Assessment of tropical cyclone rainfall from GSMaP and GPM products and their application to analog forecasting in the Philippines. Atmosphere, 13(9), 1398.',
    url: 'https://doi.org/10.3390/atmos13091398',
  },
  {
    text: 'Bracher, J., Ray, E. L., Gneiting, T., & Reich, N. G. (2021). Evaluating epidemic forecasts in an interval format. PLOS Computational Biology, 17(2), e1008618.',
    url: 'https://doi.org/10.1371/journal.pcbi.1008618',
  },
  {
    text: 'Centers for Disease Control and Prevention. (n.d.). MMWR weeks [Fact sheet].',
    url: 'https://ndc.services.cdc.gov/wp-content/uploads/MMWR_Week_overview.pdf',
  },
  {
    text: 'Department of Health. (2023). Guidelines on the prevention, control, management, and surveillance of leptospirosis (Department Memorandum No. 2023-0309).',
    url: 'https://drive.google.com/file/d/1fsclOOUcv04_vcHMefdkltFq3IkivuYo/view',
  },
  {
    text: 'Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. Journal of Business & Economic Statistics, 13(3), 253–263.',
    url: 'https://doi.org/10.1080/07350015.1995.10524599',
  },
  {
    text: 'Dimitriadis, T., Gneiting, T., & Jordan, A. I. (2021). Stable reliability diagrams for probabilistic classifiers. Proceedings of the National Academy of Sciences, 118(8), e2016191118.',
    url: 'https://doi.org/10.1073/pnas.2016191118',
  },
  {
    text: 'Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of forecast accuracy. International Journal of Forecasting, 22(4), 679–688.',
    url: 'https://doi.org/10.1016/j.ijforecast.2006.03.001',
  },
  {
    text: 'Imai, C., & Hashizume, M. (2015). A systematic review of methodology: Time series regression analysis for environmental factors and infectious diseases. Tropical Medicine and Health, 43(1), 1–9.',
    url: 'https://doi.org/10.2149/tmh.2014-21',
  },
  {
    text: 'Latigay, J. G., & Gonzaga, A. C. (2026). A hybrid Prophet-XGBoost model for weekly leptospirosis forecasting in the Philippines. In 2026 22nd IEEE International Colloquium on Signal Processing & Its Applications (CSPA) (pp. 148–153). IEEE.',
    url: 'https://ieeexplore.ieee.org/abstract/document/11517740/',
  },
  {
    text: 'Lavers, D. A., Simmons, A., Vamborg, F., & Rodwell, M. J. (2022). An evaluation of ERA5 precipitation for climate monitoring. Quarterly Journal of the Royal Meteorological Society, 148(748), 3152–3165.',
    url: 'https://doi.org/10.1002/qj.4351',
  },
  {
    text: 'Matsushita, N., Ng, C. F. S., Kim, Y., Suzuki, M., Saito, N., Ariyoshi, K., Salva, E. P., Dimaano, E. M., Villarama, J. B., Go, W. S., & Hashizume, M. (2018). The non-linear and lagged short-term relationship between rainfall and leptospirosis and the intermediate role of floods in the Philippines. PLOS Neglected Tropical Diseases, 12(4), e0006331.',
    url: 'https://doi.org/10.1371/journal.pntd.0006331',
  },
  {
    text: 'Philippine Health Insurance Corporation. (2012). PhilHealth policy recommendations on diagnosis, management and prevention of leptospirosis.',
    url: 'https://www.philhealth.gov.ph/partners/providers/pdf/Leptospirosis_Policy_Statements.pdf',
  },
  {
    text: 'Veloria, A., Perez, G. J., Tapang, G., & Comiso, J. (2021). Improved rainfall data in the Philippines through concurrent use of GPM IMERG and ground-based measurements. Remote Sensing, 13(15), 2859.',
    url: 'https://doi.org/10.3390/rs13152859',
  },
]

/** The data, maps and fonts the app is built from (check U8: each is credited). */
export const DATA_SOURCES: Reference[] = [
  {
    text: 'Bondarenko, M., et al. (2025). Constrained estimates of 2015–2030 total number of people per grid square, 100 m, R2025A v1 [Data set]. WorldPop, University of Southampton. CC BY 4.0.',
    url: 'https://doi.org/10.5258/SOTON/WP00839',
  },
  {
    text: 'Department of Health. (2026). National Health Facility Registry [Database]. Accessed 15 October 2026.',
    url: 'https://nhfr.doh.gov.ph',
  },
  {
    text: 'EOX IT Services. (2025). Sentinel-2 cloudless 2024 [Data set]. Contains modified Copernicus Sentinel data 2024. CC BY-NC-SA 4.0. The map’s satellite base map (F13).',
    url: 'https://s2maps.eu',
  },
  {
    text: 'Faeldon, J. (2024). philippines-json-maps: PSGC 2023 city and municipality outlines [Computer software]. MIT License.',
    url: 'https://github.com/faeldon/philippines-json-maps',
  },
  {
    text: 'Hersbach, H., et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999–2049.',
    url: 'https://doi.org/10.1002/qj.3803',
  },
  {
    text: 'Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. (2024). GPM IMERG Late Precipitation L3 1 day 0.1 degree x 0.1 degree V07 [Data set]. NASA GES DISC.',
    url: 'https://doi.org/10.5067/GPM/IMERGDL/DAY/07',
  },
  {
    text: 'Japan Meteorological Agency. (2026). Himawari-9 AHI band 13 clean infrared imagery, served by NASA Global Imagery Browse Services (GIBS) [Web map tiles]. The map’s live clouds (F13).',
    url: 'https://earthdata.nasa.gov/gibs',
  },
  {
    text: 'Lehner, B., & Grill, G. (2013). Global river hydrography and network routing: Baseline data and new approaches to study the world’s large river systems (HydroBASINS). Hydrological Processes, 27(15), 2171–2186.',
    url: 'https://doi.org/10.1002/hyp.9740',
  },
  {
    text: 'Mapzen. (2017). Terrain Tiles: global elevation from SRTM and other sources [Data set]. Registry of Open Data on AWS. The map’s terrain shading and 3D view (F13).',
    url: 'https://registry.opendata.aws/terrain-tiles/',
  },
  {
    text: 'NASA Global Imagery Browse Services. (2026). GPM IMERG precipitation rate (30-minute and daily) and VIIRS SNPP corrected reflectance (true color) imagery [Web map tiles]. NASA EOSDIS. The map’s rain and satellite photo layers (F13).',
    url: 'https://earthdata.nasa.gov/gibs',
  },
  {
    text: 'OCHA Philippines. (2025). Philippines subnational administrative boundaries (COD-AB, v03) [Data set]. Humanitarian Data Exchange.',
    text: 'OCHA Philippines. (2025). Philippines subnational administrative boundaries (COD-AB, v03) [Data set]. Humanitarian Data Exchange. From NAMRIA and PSA. CC BY-IGO.',
    url: 'https://data.humdata.org/dataset/cod-ab-phl',
  },
  {
    text: 'OCHA Philippines. (n.d.). Philippines population by single-year age, sex and barangay, 2020 census [Data set]. Humanitarian Data Exchange. From PSA. CC BY.',
    url: 'https://data.humdata.org/dataset/popn-single-year-age-sex-and-barangay-census-2020',
  },
  {
    text: 'OpenFreeMap. (2026). Positron map style and vector tiles, in the OpenMapTiles schema [Web map]. Map data © OpenStreetMap contributors, ODbL. The map’s street map (F13).',
    url: 'https://openfreemap.org',
  },
  {
    text: 'OpenStreetMap contributors. (2026). OpenStreetMap [Data set]. Open Database License (ODbL).',
    url: 'https://www.openstreetmap.org/copyright',
  },
  {
    text: 'Parreño, S. J. (2023). Philippine epidemiological data (Version 1) [Data set]. Mendeley Data.',
    url: 'https://doi.org/10.17632/v98325dpxv.1',
  },
  {
    text: 'Philippine Statistics Authority. (n.d.). 2024 Census of Population: Population by barangay, National Capital Region [Data set].',
    url: 'https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president',
  },
  {
    text: 'Philippine Statistics Authority. (2026). Registered live births by usual residence of mother, Philippines: 2024 [OpenSTAT table 1A1ABIB8].',
    url: 'https://openstat.psa.gov.ph',
  },
  {
    text: 'RainViewer. (2026). Weather Maps API: radar composites, past 2 hours [Web map tiles]. Free for personal and educational use. The map’s live radar (F13).',
    url: 'https://www.rainviewer.com/api.html',
    text: 'Quezon City Epidemiology and Surveillance Division. (2026). Leptospirosis cases in Quezon City by date of onset, 2015–2026 [Unpublished data, shared on request]. The app and its code hold weekly totals only.',
  },
  {
    text: 'UP Resilience Institute & NOAH Center. (n.d.). Project NOAH flood hazard maps, 5-, 25- and 100-year rain return, Metro Manila [Data set]. ODbL.',
    url: 'https://noah.up.edu.ph',
  },
  {
    text: 'Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo. ECMWF IFS forecasts and ERA5, CC BY 4.0.',
    url: 'https://doi.org/10.5281/zenodo.7970649',
  },
  {
    text: 'Figtree and Instrument Sans (the logo’s wordmark), Google Fonts. SIL Open Font License.',
    url: 'https://fonts.google.com/specimen/Figtree',
  },
]

/**
 * F12: Home's four photos (home/photos.ts), each with its author, its licence and what was
 * changed, as Home's footer says (check U8).
 */
export const PHOTO_SOURCES: Reference[] = [HERO_PHOTO, ...STRIP_PHOTOS].map((photo) => ({
  text:
    `${photo.credit.author}. ${photo.credit.title} [Photograph]. Wikimedia Commons. ${photo.credit.license}; ` +
    `${photo === HERO_PHOTO ? 'cropped and resized' : 'resized'} for Home.`,
  url: photo.credit.source,
}))
