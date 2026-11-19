# First forecasting pilot

Run date: November 1, 2026. This is a verified progress report from an executed pilot, not a final answer to the research question.

## What now works

The local repository is connected to `https://github.com/nreddi2/housingpredictability` on `codex/forecasting-pilot`. The analysis downloads and verifies source snapshots, reshapes county data, aligns mortgage rates, and runs Nixtla forecasts with a chronological validation design.

The Zillow file contains all 100 North Carolina counties. Mecklenburg County has 321 observed months, from 2000-01-31 through 2026-09-30, with no missing months. Across NC, 24 counties have all 321 observations, and 25 have gaps between their first and last available values. Presence in the file alone does not establish suitability.

## Evaluation design

Each model makes twelve separate one-month forecasts for October 2024 through September 2025. At each step, fitting uses only preceding observations. The latest twelve months, October 2025 through September 2026, remain reserved and have not been used for model evaluation or selection.

StatsForecast runs the last-value baseline (Naive), random walk with drift (RWD), and AutoARIMA. MLForecast runs Ridge, Random Forest, and histogram gradient boosting with lags of monthly home-value changes. It converts the predictions back to dollar levels. Each ML model runs twice: historical changes alone, then historical changes plus the previous month's mortgage rate and rate change. All metrics refer to home-value levels, not changes.

## Measured results

| Model | MAE ($) | RMSE ($) | MAPE (%) |
|---|---:|---:|---:|
| AutoARIMA | 160.83 | 196.20 | 0.0382 |
| Ridge_with_rates | 190.50 | 230.83 | 0.0453 |
| Ridge_history_only | 190.53 | 233.70 | 0.0452 |
| RandomForest_history_only | 264.99 | 339.55 | 0.0631 |
| RandomForest_with_rates | 268.00 | 342.64 | 0.0638 |
| GradientBoosting_history_only | 268.60 | 326.53 | 0.0639 |
| GradientBoosting_with_rates | 331.47 | 418.18 | 0.0787 |
| Naive | 481.06 | 654.57 | 0.1145 |
| RWD | 1,239.66 | 1,351.81 | 0.2946 |

MAE is the average absolute difference between a forecast and the observed county ZHVI. RMSE gives larger misses more weight. MAPE expresses absolute error as a percentage of observed ZHVI. These are errors for an aggregate index, not errors in valuing individual houses.

AutoARIMA has the lowest MAE in these validation windows: $160.83, versus $481.06 for persistence. This is about a 66.6% reduction on these twelve targets. It has not won a final out-of-sample test.

Adding rates changes Ridge MAE from $190.53 to $190.51, a negligible difference on this pilot. It increases Random Forest MAE from $264.99 to $268.00 and gradient boosting MAE from $268.60 to $331.47. The data therefore do not show a consistent forecasting benefit from these rate features in these windows. This is a descriptive comparison, not a significance test or evidence that rates do not matter economically.

## Interpretation and limits

Our interpretation: the basic data pipeline and time series modeling approach are feasible. A useful presentation can show the actual model comparison and explain why a baseline matters.

The error percentages are very small. The target is a smoothed, seasonally adjusted county index over a short forecast horizon, and the validation interval is only twelve months. These results do not establish that individual home prices are easy to forecast, that longer horizons work equally well, or that the model generalizes to other counties.

All forecasts use the downloaded revised series. We have not reconstructed historical data releases or proven what exact values were available at each real-world issue date. The current evaluation prevents ordinary future-row leakage but does not remove revision or publication-timing limitations.

No ACS income file has been downloaded: the API redirected requests to a page requiring an API key. No affordability ratios, income groups, or group-error conclusions have been calculated. The source bibliography still needs at least ten peer-reviewed papers confirmed in Atkins. Instructor approval and group-size decisions remain outstanding.

## Figures available for the midterm

1. `output/pilot/01_home_values.png`: Mecklenburg development-period ZHVI.
2. `output/pilot/02_mortgage_rates.png`: national mortgage rate, with the documented methodology change marked.
3. `output/pilot/03_model_comparison.png`: all nine baseline/model configurations by MAE.
4. `output/pilot/04_validation_forecasts.png`: observed values, persistence, and AutoARIMA on the same validation targets.

These are two descriptive figures and two evaluation figures, not four EDA figures.

## What each student should be able to explain

- The forecast target is a county's monthly typical home value, and this is a regression task.
- Nixtla supplies forecasting tools; it is not itself one model.
- The baseline predicts that next month's index equals the last observed index.
- A random train/test split would not match the intended forecasting use.
- The final holdout remains separate from the pilot comparison.
- The full question still requires income data and several counties.

## Suggested short presentation statement

"We built a Mecklenburg County pilot using Zillow home values and Freddie Mac mortgage rates. We compared a last-value baseline with statistical and machine-learning forecasts using Nixtla. Our initial rolling validation shows that AutoARIMA performs best over twelve one-month targets, while mortgage-rate features do not consistently improve the ML models. These are preliminary results from a smoothed, revised county series. Our next step is to fix county income groups and compare forecast errors across them."

Use this statement only after both students review the code and results. It describes AI-assisted work that must be disclosed, not independent student implementation.

## Verification

The executed script checks source hashes, unique county-month keys, a complete monthly Mecklenburg sequence, positive target values, prior-month mortgage-rate alignment, matching forecast dates, finite predictions, and agreement between the library's naive forecast and a manually shifted series. The four exported figures were visually inspected. Exact environment versions are in `requirements-lock.txt` and `output/pilot/run_summary.json`.

## Next work

Obtain ACS B19013 estimates and margins of error through a local API key or a Census export, define and freeze county selection, extend validation across counties and periods, and then build the presentation to its actual requirements. Keep the chosen final holdout untouched during that work.
