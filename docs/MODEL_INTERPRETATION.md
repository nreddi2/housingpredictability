# Model interpretation notes

The rate-inclusive research question uses Ridge with mortgage rates as the strongest rate-using development configuration. AutoARIMA still leads the full comparison. These notes describe Ridge behavior and do not change any model choice or final-test boundary.

## Mortgage-rate feature comparison

Each row summarizes paired county differences between the same regressor with and without mortgage-rate features. Negative MAE changes mean that adding rates reduced error. The median and mean can disagree because a few counties have larger changes.

| Family | Mean MAE change ($) | Median MAE change ($) | Counties improved (%) |
|---|---:|---:|---:|
| GradientBoosting | -10.42 | -5.69 | 59.8 |
| RandomForest | +3.19 | -0.30 | 51.1 |
| Ridge | +0.64 | -9.22 | 60.9 |

These differences provide no uniform benefit across all three families and counties. They concern these two lagged rate features and one-month forecasts; they do not establish the causal effect of rates or rule out other rate specifications.

## Coefficients

For interpretation only, Ridge was refitted on the complete development panel through September 2025. This is a single end-of-development fit, not a summary of coefficients from every rolling fold. Features and target changes are standardized as described in the walkthrough. Coefficient magnitudes are conditional on the other, correlated lag features.

| Feature | Standardized coefficient |
|---|---:|
| lag1 | +1.3775 |
| lag2 | -0.5505 |
| mortgage_rate_lag1 | -0.0967 |
| rate_change_lag1 | +0.0771 |
| lag12 | +0.0548 |
| lag3 | -0.0320 |
| lag6 | +0.0232 |

Do not interpret a mortgage-rate coefficient as a change in house-price dollars caused by a one-percentage-point rate change. These units describe transformed predictive associations.

## Error analysis

`output/panel/07_errors_over_time.png` shows the average signed and absolute percentage errors within each income group for every validation target. Shared error spikes may reflect common shocks or model limitations. They are not independent observations or proof of a causal mechanism. `ridge_group_errors_by_month.csv` preserves the underlying values.

The final holdout remains unused. Review the coefficient and residual patterns with the original series, measurement limits, and source literature before writing the final interpretation.
