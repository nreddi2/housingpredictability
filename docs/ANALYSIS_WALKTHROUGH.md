# How to understand and review the analysis

This guide explains the project in the order the analysis runs. Read it alongside `scripts/run_panel.py` and the generated findings. It describes an AI-assisted implementation that both students should inspect and understand before submitting.

## The records we analyze

One forecasting row represents one North Carolina county in one month. `unique_id` is the five-digit county FIPS identifier, `ds` is the observation month end, and `y` is Zillow's typical home value in dollars. It is an aggregate index, not a property's sale price or a literal median of transactions.

Zillow arrives as one row per county with months in columns. The code reshapes it into county-month rows. Mortgage rates arrive weekly as one national series; the code averages those weekly observations within each calendar month. It merges that same monthly series into every county.

The development panel contains January 2015 through September 2025. A county must have all 129 positive monthly home values to qualify. This leaves 92 counties. We do not fill gaps using future observations or filter on which counties forecast well.

## Income groups and affordability

Income comes from ACS table B19013. `B19013_001E` is median household income and `B19013_001M` is its published margin of error. Each ACS five-year release summarizes a collection period. For example, the 2019 release covers 2015–2019 and expresses income in 2019 dollars.

We rank all 100 counties on the fixed 2019 income estimate, set boundaries at $43,597 and $50,558, and then apply the development-coverage rule. The forecasting sample has 32 lower-income, 28 middle-income, and 32 higher-income counties. Groups never change over time. Income group is used for evaluation, not as a model input.

The main affordability comparison divides annual average 2019 ZHVI by the 2019 ACS income estimate, and does the analogous calculation for 2024. It compares two non-overlapping income periods. The housing and income observation windows still differ, so call the result a home-value-to-income proxy. Do not describe it as the share of income spent on a mortgage or as the affordability of an actual household.

## What a one-month forecast does

For the first development validation target, October 2022, training ends in September 2022. The next run trains through October 2022 and predicts November 2022. This repeats through September 2025, for 36 targets per county. This is expanding-window validation: the training history grows as time advances.

The final October 2025–September 2026 period stays outside this experiment. It is available in the raw file but is not reshaped into the development panel, fitted, plotted, or evaluated by the panel script.

The raw snapshot was downloaded in November 2026 and can contain revisions to past values. We have not reproduced historical release dates or archived data vintages. Therefore, this is a retrospective comparison, not proof of performance achievable in real time.

## The model families

| Family | What it does here | Training scope |
|---|---|---|
| Naive | Uses the last observed home value as the next forecast | Each county |
| Random walk with drift | Extends the average historical dollar change | Each county |
| AutoARIMA | Selects a nonseasonal ARIMA specification from the training history | Each county |
| Ridge | Fits a regularized linear relationship using time series features | Pooled counties |
| Random Forest | Averages predictions from multiple decision trees | Pooled counties |
| Histogram gradient boosting | Fits an additive sequence of trees | Pooled counties |

Nixtla's StatsForecast runs the statistical models. MLForecast creates the time series features and manages rolling training/prediction for the three scikit-learn regressors. Nixtla is a toolkit, not a single predictive model.

For the ML models, the code first calculates each county's monthly dollar changes, then standardizes those changes within that training fold. Features use lags of 1, 2, 3, 6, and 12 months of the transformed changes. Predictions are converted back into dollar levels before scoring. This gives the pooled models comparable training scales without assuming that a $1,000 change means the same thing in every county.

Each ML family runs with historical changes alone and with two additional features: the previous month's national mortgage-rate average and its previous-month change. Rates have identical values for every county in a given target month. These paired comparisons evaluate forecasting usefulness, not a causal effect of mortgage rates.

The pooled ML models have access to other counties' past data, while statistical models use one county at a time. This is a difference in both model family and training information. Do not attribute every performance difference to the algorithm alone.

## Reading the output tables

| Output | Main use |
|---|---|
| `county_groups_and_eligibility.csv` | Reproduce fixed income groups and see every exclusion |
| `affordability_2019_2024.csv` | Inspect each county's ratio and income-only sensitivity bounds |
| `validation_predictions.csv` | Audit individual forecast dates, targets, and predictions |
| `county_metrics.csv` | Compare each county's errors with its own baseline |
| `overall_metrics.csv` | Rank models using the predeclared equal-county metric |
| `income_group_metrics.csv` | Compare average county errors across income groups |
| `income_boundary_sensitivity.csv` | Check results after excluding uncertain group assignments |
| `mortgage_feature_comparison.csv` | Compare each regressor with and without rate features within the same county |

MAE averages absolute dollar errors. RMSE penalizes large dollar misses more strongly. MAPE averages absolute errors divided by observed ZHVI, expressed as a percentage. A model's relative MAE divides its county MAE by that county's naive MAE on the same validation months. Values below 1 beat persistence. This relative MAE is not MASE, which uses a different scaling denominator.

Group summaries weight counties equally, rather than by population, number of houses, or economic importance. The reported mean county RMSE is an average of separately computed county RMSE values, not a pooled RMSE across all observations.

## Review questions for both students

1. Why would randomly splitting monthly rows undermine the forecasting experiment?
2. What information is available to each forecast, and what remains uncertain about actual publication timing?
3. Why might absolute dollar error and percentage error tell different stories across counties?
4. Does beating the naive baseline imply a useful deployment? What other evidence would be needed?
5. What does a county-level error gap say, and what does it fail to say about households or discrimination?
6. Why can an income estimate near a group boundary make group comparisons unstable?
7. How does the choice of a smoothed target affect the interpretation of small forecast errors?

Record questions, changes, and actual student contributions as you review. The source verification notes identify publications that can support the methodology and its limitations after Atkins confirmation.
