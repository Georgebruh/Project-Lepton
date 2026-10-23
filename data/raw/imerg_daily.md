Source URL: https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary
  (catalogue: https://cmr.earthdata.nasa.gov, short_name GPM_3IMERGDL, version 07;
  subsets from https://opendap.earthdata.nasa.gov, free Earthdata login)
Downloaded on (YYYY-MM-DD): 2026-10-15
Downloaded by: a team member
Version / release: IMERG Late Run, daily, V07. Files are labelled V07B up to 2026-03-02
  and V07C from 2026-03-03; the `granule` variable in imerg_daily.nc names each day's file.
Notes: Made by `python -m src.imerg` (task A4). Box lon 120.7-121.5, lat 14.4-15.0
  (cell edges; config.IMERG_BOX, the A7 catchments plus one 0.1 degree cell), so 8 x 6 cells.
  Days 2000-06-01 (config.IMERG_START) to 2026-10-13, the latest day NASA had: 9,631 days,
  none missing, every cell with all 48 half-hours. The file is 2.2 MB; the daily
  subsets are about 345 MB.
  Variables: precipitation (mm/day, one UTC day = 8 AM-8 AM Philippine time) and
  precipitation_cnt (valid half-hours behind each value, out of 48). Values are NASA's,
  unchanged; the dates come from NASA's catalogue, not from the files' time variable.
  data/raw/imerg_daily/ holds the one-file-per-day subsets the script stacks.
  NASA's catalogue lists Late daily files back to 1998-01-01; the plan starts in June 2000.
Cite: Huffman, G.J., E.F. Stocker, D.T. Bolvin, E.J. Nelkin, J. Tan (2024), GPM IMERG Late
  Precipitation L3 1 day 0.1 degree x 0.1 degree V07, Greenbelt, MD, Goddard Earth Sciences
  Data and Information Services Center (GES DISC). doi:10.5067/GPM/IMERGDL/DAY/07
