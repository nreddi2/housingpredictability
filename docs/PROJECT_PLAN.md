# North Carolina housing affordability and forecast accuracy

Working plan dated November 1, 2026. Neelesh Reddi and Anirudh Ramesh, UNC Charlotte, DTSC 2302.

## Research question

"How has housing affordability (home values relative to household income) changed across North Carolina areas over time, and does a forecasting model using past home values and mortgage rates predict home values equally well in lower-income and higher-income areas?"

This remains the group's chosen question. The implementation below makes the unit and forecast horizon explicit without claiming the research has already answered it.

## Recommended scope

- Unit: county-month in North Carolina. Use Mecklenburg County as the initial pilot, not Charlotte city or the Charlotte metropolitan area.
- Target: monthly Zillow typical home value in dollars, all homes, middle tier, smoothed and seasonally adjusted. Forecasting is a regression task.
- First horizon: one month ahead. Add six- and twelve-month horizons only after the basic pipeline works and specify how future mortgage-rate inputs are obtained.
- Income groups: fixed 2019 ACS five-year median household income ranking across all 100 NC counties, before filtering on data coverage. The boundaries are $43,597 and $50,558; exact boundary ties go to the lower group. Compare bottom and top thirds, retaining the middle third for context.
- Geographic expansion: use all 92 counties with complete positive ZHVI values during the common January 2015–September 2025 development interval. The included groups contain 32 lower-income, 28 middle-income, and 32 higher-income counties. This replaces the provisional nine-county sample. Coverage, not forecast performance or final-holdout availability, determines inclusion. Record the eight excluded counties.
- Affordability: use annual mean 2019 and 2024 ZHVI divided by corresponding ACS five-year median household income. These income periods (2015–2019 and 2020–2024) do not overlap. The home-value-to-income proxy excludes financing costs, taxes, household debt, and within-county differences. Price and income windows differ even though dollar basis and geography match. Intermediate annual ACS releases are retained but are not treated as independent annual income changes.
- ZORI, FHFA comparisons, Prophet, neural models, and TimeGPT are optional extensions. The minimum project does not depend on them.

## Nixtla implementation

StatsForecast supplies last-value and drift benchmarks plus a nonseasonal AutoARIMA comparison. MLForecast supplies historical lag features and rolling validation for three regressors: Ridge, Random Forest, and histogram gradient boosting. The ML models forecast changes and invert predictions back to dollar levels. This keeps time ordering central while giving the report three recognizable ML models independent of whether the instructor counts ARIMA.

The pilot and panel compare each ML model with and without lagged mortgage-rate features. That comparison tests whether rates improve forecasting in this setting; it does not estimate their causal effect. In the panel, ML models pool counties after county-specific differencing and standardization within each training fold. Statistical models remain county-specific. This difference in training information must be stated when comparing them.

## Validation contract

1. Keep the raw Nov 1, 2026 snapshots unchanged and verify their hashes.
2. Reserve October 2025 through September 2026 as the final holdout; no pilot model fitting, tuning, ranking, or plots use those outcomes.
3. The original pilot uses twelve expanding-window forecasts targeting October 2024 through September 2025. The panel uses 36 targets from October 2022 through September 2025. Every forecast predicts one subsequent month and every model in an experiment uses the same target dates.
4. Fit scaling and models within each window. Use lagged home-value changes and mortgage rates from earlier months. Disable random early-stopping splits.
5. Report MAE and RMSE in dollars, MAPE in percent, and improvement over the last-value baseline. The panel's predeclared selection metric is the equal-county mean of each model's MAE divided by that county's naive MAE. This ratio is not MASE. Group summaries weight counties equally; report the average county RMSE as such, not as a pooled RMSE. Repeat group summaries after excluding counties whose income estimate ± MOE crosses a boundary.
6. These are retrospective forecasts of the current revised snapshot. Historical Zillow publication timing and data vintages are not reconstructed. A date-based split alone does not establish real-time deployability.
7. Select features and models using development data. Freeze the design before evaluating the final holdout once.

## Milestones

| Target | Deliverable | Evidence of completion |
|---|---|---|
| Nov 1 | Local repository and Mecklenburg pilot | Reproducible code, raw-file manifest, model comparison, labeled charts |
| Nov 2 before noon | Midterm submission | Presentation adapted to the actual rubric, with completed and planned work distinguished |
| Nov 8 | County selection, ACS merge, source verification | Fixed cohort, income definitions and margins of error, at least ten Atkins-confirmed papers |
| Nov 15 | Multi-county modeling | Common validation dates, baseline plus three ML models, rate-feature comparison |
| Nov 22 | Error analysis and draft report | Income-group comparisons, residual analysis, measurement limits and stakeholders |
| Nov 29 | Frozen model design and final evaluation | One final holdout evaluation and complete report draft |
| Dec 3 | Joint review | Both students can explain the code, figures, citations, and contributions |
| Dec 4 at 11:59 PM | Final Canvas submission | One member submits the 15-20 page report |

These are proposed internal milestones, not claims that either student has agreed to or completed an assignment.

## Immediate student work

Suggested division: Neelesh reviews and explains the data/forecasting code; Anirudh verifies scholarly sources and ACS definitions. Both inspect results, agree on county selection, and review the whole report. Record actual contributions as work occurs.

Instructor confirmation remains outstanding for the topic/datasets, two-person group, and model interpretation. Continue exploratory work while keeping those choices provisional. Obtain the presentation rubric before finalizing slides.

As of the latest user instruction, presentation work is deferred while the partner contributes. The active priority is the project analysis. Census access is resolved, and no additional API keys are required for the current pipeline.

## Source documentation

- Zillow definition and series options: https://www.zillow.com/research/data/
- Mortgage series and November 2022 methodology change: https://fred.stlouisfed.org/series/MORTGAGE30US
- ACS estimate periods: https://www.census.gov/programs-surveys/acs/guidance/estimates.html
- Income variable: https://api.census.gov/data/2019/acs/acs5/variables/B19013_001E.json
- Census API access requirement: https://api.census.gov/data/missing_key.html
- StatsForecast: https://github.com/Nixtla/statsforecast
- MLForecast: https://github.com/Nixtla/mlforecast
- Rolling validation: https://nixtlaverse.nixtla.io/mlforecast/docs/how-to-guides/cross_validation.html
- Target transforms: https://nixtlaverse.nixtla.io/mlforecast/docs/how-to-guides/target_transforms_guide.html

Accessed November 1, 2026. These documentation sources do not replace the ten required peer-reviewed papers.
