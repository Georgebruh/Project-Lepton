"""M4, the negative binomial model."""

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
    """sin(2 pi k t / 52.18) and cos(2 pi k t / 52.18) for k = 1..3, t = the target week's index."""
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
    """M4's rows: the rows with the inputs of each row's forecast week T joined on."""
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
    """The rows M4 fits on: the count and every input present (rows with a missing value dropped)."""
    if (rows["cases"] < 0).any():
        raise ValueError("a count is negative: a week hidden by the cutoff (S11's -999) is in the training rows")
    return rows.dropna(subset=["cases", "pop", *ALL_TERMS])


def chosen_terms(train, with_ei=True):
    """The terms M4 uses on these training rows, and the Rcum2-EI2 correlation (NaN if not computed)."""
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
    """Fit M4 (with_ei=False: M4 without EI2) on training rows: smf.negativebinomial, offset log P."""
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
    """mu for each row: exp(the fitted terms + log P), with the offset passed."""
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
    """Plot the autocorrelation of the Pearson residuals up to `lags` weeks."""
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
    """The numbers plot_residual_acf draws: the residuals' autocorrelation at lags 1..lags."""
    values, interval = acf(pearson_residuals(fit), nlags=lags, alpha=config.M4_ACF_ALPHA, result_object=False)
    return pd.DataFrame({"lag": np.arange(1, lags + 1), "autocorrelation": values[1:],
                         "band": interval[1:, 1] - values[1:]})


def main():
    """The residual check on the real counts: M4's fit at the last forecast day of the run."""
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
