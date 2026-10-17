# Notes for the team (October 18, 2026)

What everyone must know before gate C (Monday, October 19): the decisions still open, where
the code now differs from the plan, what the paper must say about it, and the rules for the
tasks still to build. Numbers below come from `python -m src.flood_exposure` and
`python -m src.checks` on the team-drive data. Dose figures are stock planning, not
prescriptions.

## 1. Decisions needed now

### 1.1 Carina gives a near-zero doses table

On IMERG's rain over the catchments, Carina is not a big storm. Its wettest 3-day total is
120.0 mm, just above R0 (119.7 mm, the rain below which nobody counts as exposed). R(5) is
239.4 mm. So Carina exposes about 1,400 people. The table below shows every storm, with
return levels fitted on the years before each storm, as the plan requires.

| Storm | 3-day total (UTC days) | Where it falls | EI | Exposed | Doxycycline 100 mg | Children's courses | Amoxicillin 500 mg |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Carina, Jul 2024 (D = 3) | 120.0 mm (22-24 Jul) | at R0 | 0.0% | 1,414 | 1,892 | 456 | 67 |
| Floods, Jul 2025 (D = 6) | 191.0 mm (17-19 Jul) | 60% of the way R0 to R(5) | 13.1% | 404,966 | 542,105 | 130,719 | 19,169 |
| Habagat, Aug 2026 (D = 4) | 141.0 mm (7-9 Aug) | 18% of the way | 4.0% | 124,765 | 167,017 | 40,273 | 5,906 |
| Kristine, Oct 2024 (D = 1) | 195.1 mm (22-24 Oct) | 63% of the way | 13.8% | 425,192 | 1,707,544 | 137,247 | 20,126 |

(Full coverage, q = u = 1; w = 0.5 for Kristine's 1-day flood. Stock planning, not
prescriptions.)

On the single wettest day (the plan's original measure) it is worse: Carina 53.7 mm and
August 2026 66.6 mm are both below R0 (about 69 mm), so both give zero.

No other way of reading IMERG rescues Carina. It stays at or below R0 with the catchment
average, the wettest single cell, or a box around QC only, over 1 or 3 days. The problem is
the satellite product, which under-reads heavy typhoon rain (section 3). Check S2 already
showed it: IMERG ranks Carina's wettest day only #10 of 2024.

**What we did:** kept Carina and added a fourth storm IMERG does register, Severe Tropical
Storm Kristine (October 2024; sources in `data/raw/storm-facts.md`). Kristine falls inside
Open-Meteo's forecast archive, so C9 can run on it too.

**Decide (whole team):**
- Confirm adding Kristine. It is not in the submitted proposal; the paper must say why it
  was added (Carina's IMERG rain sits at R0).
- The paper reports Carina's near-zero result as a finding, not hides it: satellite rain
  misses Carina's peak, so the observed-rain run cannot size stock for it. Cite Aryastana et
  al. (2022) and Veloria et al. (2021).
- Not supported by any paper, so we did not do them: lowering R0 (the plan lists tuning R0
  as future work), or switching to IMERG Final or GSMaP Gauge. Bagtasa (2022) supports
  gauge-calibrated products, but that means a new 26-year download, and IMERG Final arrives
  about 3.5 months late, so it has no August 2026.

### 1.2 C8 needs a definition of "flagged"

The plan's C8 reports "the share of flagged barangays that A11 lists as flooded, and the
share of flooded barangays that were flagged". But graded exposure (C3) gives every barangay
the same weight, and all 142 barangays have some residents in the 5-year flood zones. So as
soon as the rain passes R0, all 142 are "flagged", and both shares are meaningless
(today: 142 of 142 flagged for 2025, 2026 and Kristine).

Pick a rule before C8 is coded, write it in `config.py`, and state it in the paper. Two
simple options:
- **Top k:** flag the k barangays with the most exposed residents, with k = the number of
  barangays A11 lists for that storm. Then both shares are the same number, easy to explain.
- **Share of residents:** flag a barangay when at least X% of its residents are exposed
  (X is an assumption; report two values).

### 1.3 Kristine's flood duration is uncertain

The reports found show QC flooding on October 24, 2024 only, so D = 1 (the ±1-day test gives
D = 2). Kristine's rain started October 22. If someone can find QC DRRMO reports for October
22-23, update `start_date` and D in `config.STORMS` and in `storm-facts.md`.

## 2. Where the code differs from the plan (the paper must say these)

1. **Trigger rain is a 3-day total, not the single wettest UTC day** (C3,
   `config.RAIN_ACCUM_DAYS = 3`). The single day missed the long habagat floods of 2025 and
   2026. Return levels, storm rain and the weekly EI all use 3-day totals; the single-day run
   is kept as a comparison (`python -m src.flood_exposure --days 1`). The online plan (C3,
   C8, C9, assumptions table "Trigger rain measure") still says the single day: update it,
   and say it in E5.
2. **A storm's rain is its wettest 3-day total ending during the flood** (start_date to
   end_date in `config.STORMS`). For July 2025 that window is 17-19 July, ending the day
   flooding began. Check "A11 storm facts" tests that each storm's wettest days hold the end
   of that window.
3. **C9 forecast lead times.** A forecast made L days before a 3-day window takes the
   window's days 1, 2 and 3 from Open-Meteo's `precipitation_previous_day` L, L+1 and L+2,
   so every hour comes from a run started L days before the window. The earlier fetch used
   `previous_day1` on all three days, which mixes in runs started during the storm. A15 now
   fetches previous days 1-5 for all four storms (`forecasts_storms.csv`, column
   `previous_day`; `ecmwf.leads_covered` lists the usable leads).
4. **A11's flooded barangays were cut down** after checking every source. Many entries were
   road names read as barangays (E. Rodriguez, Don Manuel, N.S. Amoranto, Kamuning and Mangga
   are streets too; MMDA lists name roads, not barangays), or came from evacuation updates
   that name no barangay, or from later surges. Now: Carina 12, July 2025 14, August 2026 17,
   Kristine 8. Each kept barangay has a source in `data/raw/storm-facts.md`; each dropped one
   has its reason. These lists are not complete; C8's comparison is a demonstration, not a
   test (the plan already says so without barangay case counts).
5. **IMERG's partial year 2000 is kept; the refit without it changes nothing that matters.**
   Every return level moves by under 1 mm and each storm's EI by at most 0.1 point
   (`python -m src.flood_exposure --without-2000`). State both, as the plan asks.
6. **M3 reproduction (B3):** seasonal naive matches the paper's eight scores exactly, so the
   data and scored weeks are right. Prophet's MAE is 24.73 (paper 23.68, +4.4%). The hybrid's
   is 24.60 (paper 16.72, +47%), about the same as Prophet alone. Of 75 XGBoost settings
   tried, the best hybrid MAE is 21.06 and none comes within 10% of 16.72. A leak in the
   paper's XGBoost step would explain its numbers, but that is not proven. Details: `results/m3_reproduction.md`. In the paper, compare M4 with our M3 and do
   not quote 16.72 as M3's accuracy.
7. **Thresholds (B7) and M1 (B8):** a reference year's own week 53 is not used, so each year
   gives one week-52 count; week 53 of a target year uses week 52's threshold.
8. **Health centers (C7):** stock goes to health centers and barangay health stations; the
   City Health Office is not a distribution point (assumption). A barangay with several
   centers splits its need by who lives nearest each center; one with none sends it to the
   nearest center (at most 2.04 km away). The registry has two "Bago Bantay Health Center"
   entries in barangay Alicia: DOH000000000001842 (Bukidnon St., with coordinates) gets
   Alicia's need; DOH000000000008298 (84 Sto. Niño St., no coordinates) is left out. Check
   whether the second is a separate center or a duplicate entry.

## 3. Limitations and the papers behind them

- **Satellite rain under-reads typhoon peaks.** IMERG was well below Philippine rain gauges
  at the peak of five typhoons (Aryastana et al., 2022); IMERG Final "usually underestimates"
  Philippine gauges on heavy-rain days (Veloria et al., 2021). Gauge-calibrated GSMaP and
  IMERG had the lowest bias for Philippine typhoon rainfall, 2000-2021 (Bagtasa, 2022).
- **ERA5 (C9's return levels) also misses the highest daily totals**, with its largest errors
  in the tropics (Lavers et al., 2022). C9 compares forecasts with ERA5's own return levels
  (rule 3), so this affects where a forecast falls, not the comparison's fairness.
- **Catchment rain is the right area:** Marikina River floods come from rain over the upper
  watershed (Abon et al., 2011).
- **NOAH's maps do not state their design rain duration** (the metadata says nothing;
  LiPAD lists "None mm", plan correction 15). Neither 1 nor 3 days can be tied to the maps.
- R0 = 0.5 × R(5) is v2's starting value, not tuned (tuning needs DRRMO-listed floods).

References:
- Aryastana, P., Liu, C.-Y., Jou, B. J.-D., Cayanan, E., Punay, J. P., & Chen, Y.-N. (2022).
  Assessment of satellite precipitation data sets for high variability and rapid evolution
  of typhoon precipitation events in the Philippines. *Earth and Space Science, 9*(9),
  e2022EA002382. https://doi.org/10.1029/2022EA002382
- Veloria, A., Perez, G. J., Tapang, G., & Comiso, J. (2021). Improved rainfall data in the
  Philippines through concurrent use of GPM IMERG and ground-based measurements. *Remote
  Sensing, 13*(15), 2859. https://doi.org/10.3390/rs13152859
- Bagtasa, G. (2022). Assessment of tropical cyclone rainfall from GSMaP and GPM products and
  their application to analog forecasting in the Philippines. *Atmosphere, 13*(9), 1398.
  https://doi.org/10.3390/atmos13091398
- Lavers, D. A., Simmons, A., Vamborg, F., & Rodwell, M. J. (2022). An evaluation of ERA5
  precipitation for climate monitoring. *Quarterly Journal of the Royal Meteorological
  Society, 148*(748), 3152-3165. https://doi.org/10.1002/qj.4351
- Abon, C. C., David, C. P. C., & Pellejera, N. E. B. (2011). Reconstructing the Tropical
  Storm Ketsana flood event in Marikina River, Philippines. *Hydrology and Earth System
  Sciences, 15*(4), 1283-1289. https://doi.org/10.5194/hess-15-1283-2011

## 4. Rules for the tasks still to build

- **B9 (port M3):** B3 fills gaps once over the whole series, which is fine for reproducing
  the paper. In the backtest it is a leak: the seasonal baseline mu_w and the interpolation
  must use only the weeks the model may see on the forecast day (B2's view; rule 1, S11).
- **B10:** read EI from `ei_weekly.csv` rows with `fit_year` = the forecast day's year.
- **C8:** take each storm's rain with `flood_exposure.storm_peak(totals, start_date,
  end_date)` and its levels with `return_levels(maxima, year)`, then
  `doses.barangay_doses(...)` and `allocation.center_needs(...)`. Use the "flagged" rule
  from 1.2. Rerun with the continuous-exposure cut-off at 1 and 3 days.
- **C9:** for lead L, the 3-day forecast total over the storm's peak window (the same
  window C8 uses) is the sum over the window's days i = 0, 1, 2 of `previous_day` L + i.
  Fit ERA5's return levels (from `era5_daily.csv`) on years before the storm's year; never
  IMERG's. Report D = 1 and D = 7.
- **D8:** dose figures carry the label "stock planning, not prescriptions".

## 5. Data and setup

- **Upload to the team drive** (not in git): `data/raw/ecmwf_previous_runs/` (new replies for
  all four storms), `data/clean/forecasts_storms.csv` (400 rows), `data/clean/ei_weekly_no2000.csv`,
  `data/clean/center_shares_qc.csv`.
- **Checks:** with the drive data, `python -m src.checks` has no FAIL. S4, S5, S6, S7 scores
  and S11 SKIP until A13, B5, B6, D1/D3 and B10 are built. S8 lists 11 barangays whose
  exposed count falls from the 5-year map to a rarer one (Bayanihan, Malaya, Marilag,
  Pag-ibig Sa Nayon, Sacred Heart, San Jose, San Martin de Porres, Sikatuna Village,
  Teachers Village West, Villa Maria Clara, Batasan Hills); the plan asks someone to look at
  them on the map.
- **Windows setup:** install Python 3.13 and make the `.venv` in the repository root, as the
  README says. A virtual environment in a very deep folder fails with "DLL load failed ...
  The filename or extension is too long" (Windows' 260-character path limit) when importing
  netCDF4, shapely or rasterio; use a shorter path or turn on Windows long paths.
- **Case data:** `cases_weekly.csv` (A13) does not exist yet, so Layer 1's backtest cannot
  run. Follow the decision tree's last row if no QC counts arrived.
