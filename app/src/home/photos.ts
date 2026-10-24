import barangay1200 from '../assets/home/barangay-1200.webp'
import barangay800 from '../assets/home/barangay-800.webp'
import cleanup1200 from '../assets/home/cleanup-1200.webp'
import cleanup800 from '../assets/home/cleanup-800.webp'
import hero1440 from '../assets/home/hero-1440.webp'
import hero2880 from '../assets/home/hero-2880.webp'
import wading1200 from '../assets/home/wading-1200.webp'
import wading800 from '../assets/home/wading-800.webp'

/** Home's four photos, real and licensed. */

/** Who made a photo and how it may be used. */
export type PhotoCredit = {
  /** What it shows, as the credits name it. */
  title: string
  /** Its page on Wikimedia Commons, with the original and its licence. */
  source: string
  author: string
  license: string
  licenseUrl: string
}

export type Photo = {
  /** The smaller file, and both with their widths for srcSet. */
  src: string
  srcSet: string
  /** The smaller file's size, so the page keeps the photo's room while it loads. */
  width: number
  height: number
  /** What the photo shows, for screen readers. */
  alt: string
  credit: PhotoCredit
}

const CC_BY_2 = { license: 'CC BY 2.0', licenseUrl: 'https://creativecommons.org/licenses/by/2.0/' }
const CC_BY_SA_4 = { license: 'CC BY-SA 4.0', licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/' }
const AUSAID = 'AusAID (Australian Department of Foreign Affairs and Trade)'

/** The hero: a flooded Metro Manila street with residents wading, fairly dark under the shade. */
export const HERO_PHOTO: Photo = {
  src: hero1440,
  srcSet: `${hero1440} 1440w, ${hero2880} 2880w`,
  width: 1440,
  height: 680,
  alt: 'Two residents wade through a flooded street beside Pasig City Hall, pushing a wooden cart, after Typhoon Ondoy in 2009.',
  credit: {
    title: 'Pasig City after Typhoon Ondoy, 2009',
    source:
      'https://commons.wikimedia.org/wiki/File:Flooding_from_Typhoon_Ondoy_(Ketsana),_Philippines_2009._Photo-_AusAID_(10695910543).jpg',
    author: AUSAID,
    ...CC_BY_2,
  },
}

/** A photo in the row under "Why it matters", with its line of text under it. */
export type StripPhoto = Photo & { caption: string }

/** The row of three: wading, a barangay under water, clearing mud. */
export const STRIP_PHOTOS: StripPhoto[] = [
  {
    src: wading800,
    srcSet: `${wading800} 800w, ${wading1200} 1200w`,
    width: 800,
    height: 600,
    alt: 'Residents with umbrellas wade through knee-deep floodwater in Quiapo, Manila, during the July 2024 floods of Typhoon Carina and the southwest monsoon.',
    caption: 'Wading home through a flooded street',
    credit: {
      title: 'Quiapo, Manila, July 2024',
      source: 'https://commons.wikimedia.org/wiki/File:Quiapo,_Manila_Floods_Habagat-Carina_2024-1.jpg',
      author: 'Michael Peronce',
      ...CC_BY_SA_4,
    },
  },
  {
    src: barangay800,
    srcSet: `${barangay800} 800w, ${barangay1200} 1200w`,
    width: 800,
    height: 600,
    alt: 'E. Rodriguez Sr. Avenue in Damayang Lagi, Quezon City, under floodwater after a heavy downpour in September 2023.',
    // Says "after a typhoon"; this flood came from a downpour, so the line says so
    caption: 'A Quezon City barangay under water after heavy rain',
    credit: {
      title: 'Damayang Lagi, Quezon City, September 2023',
      source: 'https://commons.wikimedia.org/wiki/File:Quezon_City_(Damayang_Lagi)_flash_flood_2023-09-23.jpg',
      author: 'LMP 2001',
      ...CC_BY_SA_4,
    },
  },
  {
    src: cleanup800,
    srcSet: `${cleanup800} 800w, ${cleanup1200} 1200w`,
    width: 800,
    height: 600,
    alt: 'Residents clear mud and their belongings along a mud-covered street after the Typhoon Ondoy floods in 2009.',
    caption: 'Clearing mud once the water drops',
    credit: {
      title: 'After Typhoon Ondoy, 2009',
      source:
        'https://commons.wikimedia.org/wiki/File:Flooding_from_Typhoon_Ondoy_(Ketsana),_Philippines_2009._Photo-_AusAID_(10695651624).jpg',
      author: AUSAID,
      ...CC_BY_2,
    },
  },
]
