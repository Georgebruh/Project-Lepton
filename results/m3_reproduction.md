# B3: reproducing M3 (Latigay & Gonzaga 2026)

Code: `src/m3.py`. Rebuild: `python -m src.m3`, then `python -m src.m3 --diagnose`.
Numbers below are from `m3_reproduction.csv` and `m3_diagnostics.csv` (prophet 1.5.0,
xgboost 3.4.1). Every run gives the same numbers: Prophet's fit and XGBoost here use no
random draws.

## Result

The data setup and Prophet are reproduced; the hybrid is not.

| Model | Our MAE | Paper MAE | Gap | Within 10%? |
| --- | --- | --- | --- | --- |
| Seasonal naive | 64.1782 | 64.1782 | 0.0% | exact (all four Table I scores and all four Table II scores) |
| Prophet | 24.73 | 23.68 | +4.4% | yes |
| Hybrid (Prophet + XGBoost) | 24.60 | 16.72 | +47.1% | **no** |

Other scores (main run, 18 weeks): Prophet RMSE 30.33 (paper 28.16), SMAPE 49.76 (50.66),
bias −5.59 (+1.05). Hybrid RMSE 33.11 (21.93), SMAPE 44.30 (38.80), bias −3.26 (−0.72).
Diebold–Mariano, Hybrid vs Prophet: −0.03, p = 0.49 (paper −1.82, p = 0.043). In our copy,
XGBoost does not improve on Prophet.

## What the exact seasonal-naive match confirms

Seasonal naive has nothing to fit: its forecast is the filled value 52 weeks earlier. Matching
all eight of its published scores to four decimals confirms:

- **Series layout:** 52 rows per year with no row for ISO 2020 week 53 (the paper's "260
  observations" = 5 × 52). Keeping A9's ISO week 53 row moves every fold one week and the
  scores no longer match (run `other_week_53`).
- **Scored weeks:** 2021-W12 to 2023-W37, 9 folds of 2 weeks; peak weeks (above 186) are
  2023-W36 and W37.
- **SMAPE** on the 0–200 scale: mean of 2|F − A| / (|A| + |F|), × 100.
- **Gap filling** of the 2020 weeks seasonal naive reads: W12–13 at 0.5 × μ_w (lockdown)
  and W44–45 at 1.0 × μ_w (monsoon), with μ_w averaged over 2019, 2021, 2022 and 2023.

## Readings we had to choose (config.py)

- **Lockdown dates** (`M3_LOCKDOWNS`): the paper cites a news timeline without dates. We use
  ECQ and MECQ: 15 Mar – 31 May 2020 and 4–18 Aug 2020; a week counts if its Thursday falls
  inside. Treating all of 2020's community quarantine as lockdown (`lockdown_all_2020`)
  breaks the seasonal-naive match, so the main reading is the one consistent with the paper.
- **A missing week outside both rules** (2020-W11 and W52): linear interpolation, the
  paper's third step.
- **XGBoost "defaults"**: xgboost's `xgb.train` with 100 rounds (the usual scikit-learn
  wrapper default; scikit-learn is not in our requirements), learning rate 0.3, max depth 6.
  The paper says only "low complexity". Rerun with max depth 2: hybrid MAE 26.04.

## Why the hybrid misses: likely cause

1. **No XGBoost setting closes the gap.** We tried 75 settings (max depth 1–6, 10–200
   rounds, learning rate 0.05–0.3). Hybrid MAE ranged 21.06–29.48, median 24.21; none came
   within 10% of 16.72. Only one beat Prophet at p < 0.05 (max depth 1, 10 rounds, learning
   rate 0.05: MAE 24.32 vs Prophet's 24.73, p = 0.03), a small but steady gain.
2. **A leak reproduces numbers like the paper's.** If XGBoost is also trained on the
   forecast weeks' own errors, which a real forecast cannot know, hybrid MAE ranges
   0.02–23.95 with a median of 16.02, and 11 of the 75 settings land within 10% of 16.72.
   The paper's Table II also looks too good for an honest forecast: hybrid peak-week SMAPE
   2.8% while Prophet's is 19.1%, and the paper calls the improvement "counter-intuitive".
3. **Prophet itself is close but not identical** (bias −5.59 vs +1.05). The paper may have
   used R for more than SARIMA (it ran `auto.arima()` in R); R's prophet and xgboost
   packages can differ from Python's in versions and defaults.

Our reading: the published hybrid gain cannot be reached from the method as described. A
leak in the XGBoost step is consistent with the numbers but **not proven**; only the
authors' code can settle it. Asking them for it (jglatigay@up.edu.ph) is worth one email.

## What this means for LEPTON

- Per B3's done condition, the gap and its likely cause are now written down, so B9 can
  port M3 to QC with these exact settings (main run).
- In the primary endpoint (D5), M4 is compared with our honest M3, which on this data is
  about as accurate as Prophet alone. The paper should say that we could not reproduce the
  published hybrid gain and cite this note, rather than quote 16.72 as M3's accuracy.
- SARIMA (Table I) was not reproduced: it is not part of M3, and the paper used R's
  `auto.arima()`.
