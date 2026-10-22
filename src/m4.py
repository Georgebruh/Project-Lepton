"""M4, the negative binomial model (task B5).

M4 forecasts the target week's expected cases mu from the season, recent cases, rain and
flood exposure, with QC's population as an offset. One city, so v2's city terms drop out:

    log mu(T + h) = log P(T) + b0
                    + sum over k = 1..3 of [a_k sin(2 pi k t / 52.18) + c_k cos(2 pi k t / 52.18)]
                    + rho log(1 + y~) + b1 Rcum2(T) / 50 + b2 EI2(T) + delta COVID(T + h)

  P(T)      QC's population in the forecast week T (B1). It is an offset: its coefficient
            is fixed at 1, so the other terms describe cases per resident.
  t         the target week's continuous week index (A3). k = 1..3 (config.FOURIER_K) and
            52.18 weeks a year (config.WEEKS_PER_YEAR): the season, as three pairs of waves.
  y~        recent cases, the two newest counts the model may see (B2's column `recent`).
  Rcum2(T)  rain over QC in weeks T - 1 and T, in mm (B4), divided by 50
            (config.RAIN_SCALE_MM): b1 is the change in log mu per 50 mm.
  EI2(T)    the larger exposure index of weeks T - 1 and T, in % of QC residents (B4, from C3).
  COVID     1 for target weeks in 2020-2021 (config.COVID_YEARS), else 0.

In plain words: expected cases = population x base rate x season x a momentum multiplier
x a rain multiplier x a flood multiplier x a COVID multiplier. The momentum multiplier is
(1 + y~)^rho: with rho = 0.3, twice the recent cases multiply next week's by 2^0.3 = 1.23.

The count is negative binomial with mean mu and variance mu + alpha mu^2 (NB2), fitted by
maximum likelihood; theta = 1 / alpha is the spread B6 uses (forecast_range.forecast_dist).

Rules this file follows:
  - smf.negativebinomial, not the GLM family, which fixes alpha at 1 (rule 4).
  - The offset log P is passed when fitting AND when predicting (rule 4). Left out of the
    prediction, statsmodels returns about 1/3,000,000 of the real mean, with no error.
  - Rows with a missing value are dropped before fitting; a forecast row with a missing
    input stops the run instead of giving NaN (rule 5). A negative count stops too: S11's
    -999 would mean a week hidden by the cutoff got into the training rows (rule 1).
  - If Rcum2 and EI2 correlate above 0.8 in the training rows (config.RAIN_EI_MAX_CORR,
    either sign), Rcum2 is left out and EI2 kept alone (v2).
  - A term with the same value in every training row cannot be estimated, so it is left
    out (assumption): COVID on forecast days before 2020, EI2 if it is 0 in every row.
    A forecast then gets no such term (a 2020 target before any COVID week: delta = 0).
  - M4 without EI2, the flood test (D6), is fit on exactly the same rows. It keeps Rcum2
    even when M4 leaves Rcum2 out (reading), so the test compares the flood index with
    rain, never with nothing.

Inputs come as tables (model_rows): B2's rows, B4's weekly rain and exposure, B1's
population. B10 calls model_rows, fit_m4 (M4 and M4 without EI2) and predict_m4 at
every forecast day. v2's residual check runs once, after B10, on M4's fit at the run's
last forecast day:

    python -m src.m4      # results/m4_residual_acf.png and m4_residual_acf.csv

Check: python -m src.checks (S5: 50 made-up datasets of 400 weeks recover the true values).
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.tsa.stattools import acf

import config

SEASON = [f"{wave}{k}" for k in range(1, config.FOURIER_K + 1) for wave in ("sin", "cos")]
RECENT = "log_recent"   # log(1 + y~): coefficient rho
RAIN = "rcum2_50"       # Rcum2 / 50: coefficient b1
EI = "ei2"              # EI2: coefficient b2
COVID = "covid"         # coefficient delta
ALL_TERMS = [*SEASON, RECENT, RAIN, EI, COVID]
SHOW_LAGS = 3           # lags main() prints; the plot and its table hold config.M4_ACF_LAGS


def season_terms(week_index):
    """sin(2 pi k t / 52.18) and cos(2 pi k t / 52.18) for k = 1..3, t = the target week's index.

    Returns columns sin1, cos1, sin2, cos2, sin3, cos3 with week_index's index.
    """
    t = pd.Series(week_index, dtype=float)
    out = pd.DataFrame(index=t.index)
    for k in range(1, config.FOURIER_K + 1):
        angle = 2 * np.pi * k * t / config.WEEKS_PER_YEAR
        out[f"sin{k}"] = np.sin(angle)
        out[f"cos{k}"] = np.cos(angle)
    return out


def one_row_per_week(table, name):
    """Stop if a weekly input table lists a week twice: the join would copy rows."""
    if table["week_index"].duplicated().any():
        raise ValueError(f"the {name} table lists a week twice")


def model_rows(targets, features, pop):
    """M4's rows: B2's rows with the inputs of each row's forecast week T joined on.

    targets: B2's training_rows or prediction_row (week_index, year, cases, forecast_week,
    recent); forecast_week = target - h, the week whose rain, exposure and population the
    row reads (rain is never guarded, B2). features: one row per week with week_index,
    rcum2 (mm) and ei2 (%) (B4; EI2 from the ei_weekly.csv fit year of the forecast day,
    C3). pop: one row per week with week_index and pop (B1's pop_weekly.csv).
    Adds pop, rcum2, ei2, the terms log_recent = log(1 + y~), rcum2_50 = Rcum2 / 50, covid,
    and the season terms. One row out per row in; an input the tables lack stays NaN
    (fit_m4 drops the row, predict_m4 stops).
    """
    one_row_per_week(features, "features")
    one_row_per_week(pop, "population")
    by_week = (features[["week_index", "rcum2", EI]]
               .merge(pop[["week_index", "pop"]], on="week_index", how="outer")
               .rename(columns={"week_index": "forecast_week"}))
    rows = targets.drop(columns=["pop", "rcum2", EI], errors="ignore").merge(by_week, on="forecast_week", how="left")
    if len(rows) != len(targets):
        raise ValueError(f"{len(targets)} rows in, {len(rows)} out: the join copied rows")
    rows[RECENT] = np.log1p(rows["recent"])
    rows[RAIN] = rows["rcum2"] / config.RAIN_SCALE_MM
    rows[COVID] = rows["year"].isin(config.COVID_YEARS).astype(int)
    return rows.join(season_terms(rows["week_index"]))


def complete_rows(rows):
    """The rows M4 fits on: the count and every input present (rows with a missing value dropped).

    The same rows for M4 and M4 without EI2, so the flood test compares like with like.
    Stops on a negative count (rule 1: S11's -999 means a hidden week got in).
    """
    if (rows["cases"] < 0).any():
        raise ValueError("a count is negative: a week hidden by the cutoff (S11's -999) is in the training rows")
    return rows.dropna(subset=["cases", "pop", *ALL_TERMS])


def chosen_terms(train, with_ei=True):
    """The terms M4 uses on these training rows, and the Rcum2-EI2 correlation (NaN if not computed).

    All terms (without EI2 for the flood test), minus any with the same value in every
    row, minus Rcum2 when M4 has EI2 and the two correlate above config.RAIN_EI_MAX_CORR.
    """
    terms = [term for term in ALL_TERMS if with_ei or term != EI]
    terms = [term for term in terms if train[term].nunique() > 1]
    corr = train[RAIN].corr(train[EI]) if RAIN in terms and EI in terms else np.nan
    if with_ei and abs(corr) > config.RAIN_EI_MAX_CORR:
        terms.remove(RAIN)
    return terms, corr


def good_fit(result):
    """True when the optimizer converged, every coefficient is a finite number and alpha is above 0."""
    params = result.params
    return bool(result.mle_retvals["converged"]) and bool(np.isfinite(params).all()) and params["alpha"] > 0


def fit_m4(rows, with_ei=True):
    """Fit M4 (with_ei=False: M4 without EI2) on training rows: smf.negativebinomial, offset log P.

    rows: model_rows of B2's training rows. Tries the optimizers in config.M4_FIT_METHODS in
    turn until one gives a good fit (good_fit). Returns a dict:
      result        statsmodels' fit (result.params: one coefficient per term, and alpha)
      terms         the terms used (chosen_terms)
      theta         1 / alpha, the spread of the fit (B6's fallback)
      corr_rain_ei  the Rcum2-EI2 correlation on the rows (NaN if one of them was left out)
      rows, dropped rows used, and rows dropped for a missing value
      method        the optimizer that gave the fit
    Stops if no optimizer gives a good fit, or there are too few rows for the coefficients.
    """
    train = complete_rows(rows)
    terms, corr = chosen_terms(train, with_ei)
    if len(train) <= len(terms) + 2:   # + intercept + alpha
        raise ValueError(f"{len(train)} complete rows: too few to fit {len(terms) + 2} coefficients")
    model = smf.negativebinomial("cases ~ " + " + ".join(terms), data=train, offset=np.log(train["pop"]))
    for method in config.M4_FIT_METHODS:
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):   # a failed try is checked below
            result = model.fit(method=method, maxiter=config.M4_MAX_ITER, disp=0)
        if good_fit(result):
            return {"result": result, "terms": terms, "theta": 1 / result.params["alpha"], "corr_rain_ei": corr,
                    "rows": len(train), "dropped": len(rows) - len(train), "with_ei": with_ei, "method": method}
    raise ValueError(f"M4 found no good fit with {config.M4_FIT_METHODS} in {config.M4_MAX_ITER} iterations "
                     f"({len(train)} rows)")


def predict_m4(fit, rows):
    """mu for each row: exp(the fitted terms + log P), with the offset passed (rule 4).

    rows: model_rows of B2's prediction row (or any rows with the fit's terms and pop).
    Stops if an input the fit uses is missing, or a forecast is not a finite number (rule 5).
    """
    needed = ["pop", *fit["terms"]]
    gaps = rows[needed].isna()
    if gaps.any().any():
        raise ValueError(f"M4 forecast for week index {list(rows.loc[gaps.any(axis=1), 'week_index'])}: "
                         f"missing {list(gaps.columns[gaps.any()])}")
    mu = np.asarray(fit["result"].predict(rows, offset=np.log(rows["pop"])), dtype=float)
    if not np.isfinite(mu).all():
        raise ValueError("an M4 forecast is not a finite number")
    return mu


def pearson_residuals(fit):
    """(y - mu) / sqrt(mu + mu^2 / theta) on the training rows, in their order (oldest first)."""
    result = fit["result"]
    mu = np.asarray(result.predict(), dtype=float)   # in-sample: uses the fit's own offset
    y = np.asarray(result.model.endog, dtype=float)
    return (y - mu) / np.sqrt(mu + mu ** 2 / fit["theta"])


def plot_residual_acf(fit, path=config.M4_RESIDUAL_ACF, lags=config.M4_ACF_LAGS):
    """Plot the autocorrelation of the Pearson residuals up to `lags` weeks (v2's second check).

    In plain words: if this week's miss tells you next week's, the bars at lags 1, 2, ...
    stand outside the shaded band, and M4 is missing some week-to-week momentum. Rows
    dropped for a missing value are skipped, so lags count rows, not weeks. Saved via a
    .part file, so a stopped run never leaves half a picture.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.graphics.tsaplots import plot_acf

    fig, ax = plt.subplots(figsize=(7, 3.5))
    plot_acf(pearson_residuals(fit), lags=lags, ax=ax, alpha=config.M4_ACF_ALPHA,
             title=f"M4{'' if fit['with_ei'] else ' without EI2'}: residual autocorrelation ({fit['rows']} weeks)")
    ax.set_xlabel("lag (weeks)")
    part = path.with_suffix(".part")
    fig.savefig(part, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    part.replace(path)
    return path


def residual_acf(fit, lags=config.M4_ACF_LAGS):
    """The numbers plot_residual_acf draws: the residuals' autocorrelation at lags 1..lags.

    Columns lag, autocorrelation and band. In plain words: autocorrelation is how much one
    week's miss says about the miss `lag` weeks later (0: nothing, 1: the same miss), and
    band is half the width of the plot's shaded range around 0, where 95% of them would
    fall if the weeks' misses were independent (config.M4_ACF_ALPHA). The band widens a
    little with the lag (Bartlett's formula, as plot_acf draws it).
    """
    values, interval = acf(pearson_residuals(fit), nlags=lags, alpha=config.M4_ACF_ALPHA, result_object=False)
    return pd.DataFrame({"lag": np.arange(1, lags + 1), "autocorrelation": values[1:],
                         "band": interval[1:, 1] - values[1:]})


def main():
    """v2's residual check (B5) on the real counts: M4's fit at the last forecast day of B10's run.

    Refits M4 there on the rows B2 lets it see, with the run's own data option and g and
    that day's rain and EI (its fit year, C3), as B10 did; the fit has no random draws, so
    it is the run's own fit. Saves the plot (config.M4_RESIDUAL_ACF) and its numbers
    (config.M4_RESIDUAL_ACF_TABLE, via a .part file) and prints the first lags. Needs
    B10's results/forecasts.csv.
    """
    from src import backtest, view, weeks   # backtest imports this file, so it is imported here, not at the top

    if not config.FORECASTS.exists():
        raise FileNotFoundError(f"{config.FORECASTS} not found: run B10 first (python -m src.backtest)")
    run = pd.read_csv(config.FORECASTS, usecols=["option", "g", "forecast_week"])
    if len(run[["option", "g"]].drop_duplicates()) != 1:
        raise ValueError(f"{config.FORECASTS.name} holds more than one data option or guard: one run per file")
    option, g, T = run["option"].iloc[0], int(run["g"].iloc[0]), int(run["forecast_week"].max())
    cases, features, pop = backtest.load_cases(), backtest.load_features(), backtest.load_population()
    rain = backtest.features_for(features, weeks.year_week(T)[0])
    fit = fit_m4(model_rows(view.training_rows(cases, T, option, g), rain, pop))

    picture = plot_residual_acf(fit)
    table = residual_acf(fit)
    part = config.M4_RESIDUAL_ACF_TABLE.with_suffix(".part")
    table.round(4).to_csv(part, index=False)
    part.replace(config.M4_RESIDUAL_ACF_TABLE)

    shown = table.head(SHOW_LAGS)
    print(f"M4 at the last forecast day of {config.FORECASTS.name}, {weeks.year_week(T)} (year, week), option "
          f"{option}" + (f", g = {g}" if option == "C" else "") + f": {fit['rows']} training weeks")
    print("residual autocorrelation: " + ", ".join(f"lag {row.lag} {row.autocorrelation:.2f}" for row in shown.itertuples())
          + f"; independent weeks stay within +/-{shown['band'].iloc[0]:.2f} at lag 1 (95%)")
    print(f"wrote {picture} and {config.M4_RESIDUAL_ACF_TABLE}")


if __name__ == "__main__":
    main()
