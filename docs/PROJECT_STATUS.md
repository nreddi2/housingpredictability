## November 19 update

The reserved year has now been evaluated under the versioned protocol in config/final_evaluation.md. The current findings, figures, reproduction steps and student review items are in the root README and the results directory. All subsequent text in this file is the historical November 1 status.

# Project status — November 1, 2026

Latest user correction: the source-count and instructor-decision action items below are outdated historical context, not current pending tasks. Current presentation priorities are longer forecasts, county/month error investigation, evaluation on the reserved year, and the final report. Specific source and instructor records were not independently rechecked in this revision.

The first development analysis is implemented and executed. The research project is not complete. This status describes repository artifacts, not independently verified student contributions.

## Completed technical work

- Local Git repository, Python environment, reproducible download/modeling scripts, dependency records, and raw-data provenance.
- Zillow county ZHVI, Freddie Mac mortgage rates via FRED, and ACS income estimates/margins of error; eligibility checks for all 100 NC counties and a fixed 92-county development cohort.
- Fixed 2019 income groups; 2019 versus 2024 affordability-proxy comparison using non-overlapping ACS periods.
- Mecklenburg pilot followed by 36 rolling one-month validation targets for 92 counties. Nine configurations cover two simple benchmarks, AutoARIMA, and three ML regressors with/without rates.
- Initial overall and income-group errors, mortgage-feature comparison, income-boundary sensitivity check, error-by-month plots, and descriptive Ridge coefficient analysis.
- Source verification notes, analysis explanations, AI assistance log, and midsemester presentation.

Evidence: output/panel/run_summary.json, docs/PANEL_FINDINGS.md, config/panel_design.json, and output/panel tables. The run summary explicitly records final_holdout_evaluated = false.

## Remaining work

1. Student review and research decisions: both students must understand and check the code, reproduce key results, and confirm instructor expectations for the question/data and two-member group. Three recognizable ML regressors already exist; adding more models solely to increase the count is unnecessary.
2. Complete the literature review: verify at least ten peer-reviewed sources in Atkins, read relevant passages, synthesize findings, and connect them to the choices and social interpretation. Correct the previously identified scholarly-worksheet problems honestly.
3. Strengthen the analysis: test six- and twelve-month horizons if retained in scope, including a defensible treatment of unavailable future mortgage rates; examine the stability of group gaps across time, counties, and metrics. Some error and sensitivity analyses already exist, so build on them rather than presenting them as entirely unstarted.
4. Resolve measurement limits: assess feasible checks for smoothing/revision effects and excluded counties. Historical real-time vintages may be unavailable; document that limitation rather than promising to eliminate it. Address the different information available to pooled ML and county-specific statistical models.
5. Freeze the design and evaluate the final holdout: choose models/metrics using development data, then evaluate October 2025–September 2026 without tuning to the holdout. Final conclusions may differ from the current development results.
6. Write the 15–20 page report: all required sections, interpreted figures, dataset/measurement details, model comparisons, societal implications, limitations, APA references, and technical appendix. Review whether all final assignment specifications are covered.
7. Finish reproducibility and submission: verify the code from a clean setup, make the runnable repository accessible for submission, confirm AI disclosure against course policy, record each member's actual contributions, and jointly review the entire report.

## Honest midsemester framing

“We have completed the data pipeline and an initial one-month forecasting comparison. Next we will test the reliability of the findings, complete the literature synthesis, and evaluate a reserved test year before writing our final conclusions.”

Longer horizons and robustness work should serve the question. Prophet, TimeGPT, neural models, rental data, and additional datasets are optional, not prerequisites for finishing a strong project. Do not conceal completed work or add unnecessary scope just to appear less advanced.
