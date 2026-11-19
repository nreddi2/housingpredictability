# North Carolina housing affordability and forecast accuracy

UNC Charlotte · DTSC 2302 Modeling and Society · Neelesh Reddi and Anirudh Ramesh

[Reserved-year results](results/final/overall.csv) · [Income-group accuracy](results/final/groups.csv)

Across 92 eligible counties, the median typical-home-value-to-income ratio rose in every fixed income group from 2019 to 2024. The final evaluation tested 12 one-month forecasts per county, October 2025 through September 2026. The Ridge model using earlier home values and mortgage rates had mean county MAE of **$360.47**, versus **$719.59** for repeating the last value. Its MAPE averaged **0.251% in lower-income counties** and **0.082% in higher-income counties**. These results describe one year of retrospective index forecasts using a revised data vintage. Data Provided by Zillow Group.

## Reproduce scores directly from this checkout

Use Python 3.12 on Windows PowerShell:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/summarize_final.py
~~~

On macOS or Linux use the virtual environment’s bin/python. The summary script reads the committed [forecast error records](results/final/forecast_errors.csv). It regenerates overall, county, income-group, sensitivity and monthly scores. No API key or raw downloads are needed for this step.

## Refit the experiments from source

The original 12 November 1 input files are held by the group. Copy them to data/raw/ alongside the [tracked manifest](data/raw/pilot_download_manifest.json). It lists public provider URLs, filenames, retrieval timestamps and hashes. Zillow and FRED revise live files. Contact the group for access to the exact snapshot for a byte-identical refit. A refreshed vintage is a different experiment. The download script documents acquisition and uses the local CENSUS_API_KEY environment variable only for new Census requests.

~~~powershell
.\.venv\Scripts\python.exe scripts/run_panel.py
.\.venv\Scripts\python.exe scripts/verify_panel.py
.\.venv\Scripts\python.exe scripts/interpret_panel.py
.\.venv\Scripts\python.exe scripts/run_final.py
~~~

The [development plan](config/panel_design.json) specifies the 92-county cohort, three ML regressors, statistical benchmarks, and 36 expanding monthly validation windows. The [final protocol](config/final_evaluation.md) was committed before examining the reserved outcomes. The code fits each model through the prior month, predicts one month ahead, and verifies the county-month keys and naive predictions against observed data. The [development summaries](results/development/) and [figures](report/figures/) document model selection and affordability. The development summaries and historical worksheets describe the earlier phase of the project.

Dependencies include Nixtla MLForecast and StatsForecast. Zillow Research supplies ZHVI, Freddie Mac via FRED supplies MORTGAGE30US, and the Census Bureau supplies ACS five-year table B19013. See [the analysis walkthrough](docs/ANALYSIS_WALKTHROUGH.md) and raw manifest for data access and measurement limitations.

## Student review

The technical evaluation is complete. The group must confirm its sources in Atkins, complete its actual contribution statement and jointly review the report and AI disclosure before submission.
