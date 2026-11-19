# Multi-county development findings

Executed November 1, 2026. All results are preliminary development results. The final October 2025–September 2026 holdout remains unevaluated.

## Data and cohort

Census income estimates and margins of error cover 100 NC counties in each 2015–2024 ACS five-year release. 92 counties meet the predeclared requirement of 129 complete, positive monthly ZHVI values from January 2015 through September 2025. All eligible counties are included; none were selected by forecast performance.

Income groups use fixed 2019 estimates ranked across all 100 counties. This represents the 2015–2019 income period, not a single-year survey. Eligibility uses development data only. Excluded counties: Stanly County, Burke County, Chowan County, Robeson County, McDowell County, Avery County, Watauga County, Alamance County.

## Modeling design

Each model predicts the next month at 36 expanding training cutoffs, giving 3312 county-month forecasts per model from October 2022 through September 2025. Statistical models fit separately to each county. ML models pool counties, with county-specific differencing and standardization fitted anew within each training window. No income group is a predictor. Mortgage features use the preceding month.

This differs from the Mecklenburg pilot in its common start date, longer validation interval, pooled ML training, and target standardization. The results are not an apples-to-apples comparison with the pilot. Pooled ML also has access to other counties' training histories, unlike the local statistical models.

The predeclared selection metric is the equal-county mean of model MAE divided by that county's naive MAE. A value below 1 indicates lower average relative error. This avoids selecting only on dollar errors dominated by more expensive markets.

| Model | Mean relative MAE | Mean county MAE ($) | Mean county MAPE (%) | Counties beating naive (%) |
|---|---:|---:|---:|---:|
| AutoARIMA | 0.393 | 426.38 | 0.185 | 100.0 |
| Ridge_with_rates | 0.461 | 504.03 | 0.214 | 100.0 |
| Ridge_history_only | 0.464 | 503.39 | 0.216 | 100.0 |
| GradientBoosting_with_rates | 0.487 | 530.96 | 0.223 | 100.0 |
| GradientBoosting_history_only | 0.497 | 541.38 | 0.230 | 100.0 |
| RandomForest_with_rates | 0.504 | 552.23 | 0.235 | 100.0 |
| RandomForest_history_only | 0.505 | 549.05 | 0.234 | 100.0 |
| Naive | 1.000 | 1,116.07 | 0.461 | 0.0 |
| RWD | 1.169 | 1,281.56 | 0.514 | 27.2 |

## Income-group error comparison

The development leader by the predeclared metric is AutoARIMA. Its group results follow. These are equal-county averages, not population-weighted household outcomes.

| 2019 income group | Counties | Mean county MAE ($) | Mean county RMSE ($) | Mean county MAPE (%) | Mean relative MAE |
|---|---:|---:|---:|---:|---:|
| Lower | 32 | 489.88 | 604.43 | 0.282 | 0.471 |
| Middle | 28 | 415.96 | 520.63 | 0.164 | 0.362 |
| Higher | 32 | 371.99 | 479.96 | 0.105 | 0.341 |

The lower-minus-higher MAPE difference is +0.176 percentage points. This is a descriptive difference over these counties and dates, not evidence of discrimination or a causal income effect. Counties share economic shocks and are not independent random observations. No significance claim is made.

40 eligible counties have estimate-plus/minus-MOE intervals crossing a fixed income boundary. `income_boundary_sensitivity.csv` repeats the group summaries after excluding these counties. This is a sensitivity check, not a confidence interval for group membership: the boundary estimates also have uncertainty.

## Affordability proxy

The main comparison uses non-overlapping ACS periods: 2015–2019 and 2020–2024. Annual average 2019 and 2024 ZHVI values are divided by each corresponding end-year-dollar income estimate. This is an endpoint home-value-to-income proxy with different price/income observation windows. It is not a five-year average price ratio, a household payment measure, or a literal median-house-price ratio. Ratios are dimensionless; each numerator/denominator uses its own end-year dollar basis.

| Fixed income group | Median county ratio in 2019 | Median county ratio in 2024 |
|---|---:|---:|
| Lower | 3.01 | 3.57 |
| Middle | 3.18 | 4.00 |
| Higher | 3.88 | 4.65 |

The affordability table includes sensitivity bounds using income estimate ± MOE. These reflect income uncertainty only; they are not complete confidence intervals for affordability because ZHVI uncertainty is not quantified. Annual ACS releases between the endpoints are retained for provenance, not treated as independent annual change measurements.

## Direct answer for a model that uses mortgage rates

Ridge_with_rates leads the rate-using configurations under the same relative-MAE criterion. Its comparison addresses the rate-inclusive research question; the overall leader AutoARIMA does not use rates. This is a development-model choice, not a final-test conclusion.

| Fixed income group | Counties | Mean county MAE ($) | Mean county MAPE (%) | Mean relative MAE |
|---|---:|---:|---:|---:|
| Lower | 32 | 546.91 | 0.318 | 0.528 |
| Middle | 28 | 481.62 | 0.189 | 0.419 |
| Higher | 32 | 480.76 | 0.133 | 0.430 |

Its lower-minus-higher MAPE gap is +0.185 percentage points. The group means differ descriptively. We have not established statistical significance, discrimination, or a causal explanation for the difference. Dollar errors and relative-to-baseline errors must be considered alongside MAPE.

After excluding counties whose income estimate ± MOE crosses a fixed boundary:

| Fixed income group | Retained counties | Mean county MAPE (%) | Mean relative MAE |
|---|---:|---:|---:|
| Lower | 19 | 0.338 | 0.562 |
| Middle | 4 | 0.122 | 0.306 |
| Higher | 29 | 0.118 | 0.428 |

This sensitivity analysis changes the population being summarized and leaves few middle-income counties. Treat it as a robustness description, not a corrected estimate of group fairness.

## Limits and next steps

- Zillow values are smoothed, seasonally adjusted, and retrospectively revised. Observation-date splitting does not reconstruct historical publication times or real-time data vintages.
- One-month forecasts do not establish performance at six or twelve months.
- Group-level results do not describe individuals, establish causation, or identify discrimination.
- Common-history exclusions can change which counties the study represents. Report exclusions and group counts.
- Compare history-only and rate-feature models using the paired county table before attributing any forecasting benefit to rates.
- Review these development results, select robustness checks, and freeze the full design before opening the final holdout.
- At least ten peer-reviewed sources, instructor decisions, and human review remain required.

## Reproduction and source records

`python scripts/run_panel.py` regenerates the analysis. The design is in `config/panel_design.json`; the frozen cohort and raw-data hashes are in `output/panel/cohort_frozen_before_fitting.json`. `--prepare-only` stops before training, and `--analyze-only` rebuilds tables/figures from saved predictions.

Source documentation: https://www.zillow.com/research/data/ ; https://fred.stlouisfed.org/series/MORTGAGE30US ; https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html ; https://api.census.gov/data/2019/acs/acs5/variables/B19013_001E.json . Accessed November 1, 2026. Exact source URLs without credentials and file hashes are in the raw-data manifest.

AI assistance: Codex implemented and executed this analysis, drafted the explanations, and generated the figures. Students must review, understand, and verify the work and disclose assistance according to course policy.
