# Final evaluation protocol | November 19, 2026

Chosen using only development scores through September 2025. The primary model answering the rate-inclusive question is pooled Ridge with prior mortgage rates. Compare it with last value, history-only Ridge (incremental value of rates), and the development-wide leader, county-specific nonseasonal AutoARIMA. Use the exact development transformations, settings and 92 county IDs. No holdout-based model selection.

Forecast October 2025 through September 2026 one month at a time. Refit on observations through the preceding month. Report equal-county MAE, RMSE, MAPE and MAE relative to each county’s naive MAE. Compare lower and higher groups for primary Ridge, including the previously defined income-boundary sensitivity check. Inspect monthly errors. If targets or required features are missing, report this before interpreting results. The analysis uses revised November 1 snapshots.
