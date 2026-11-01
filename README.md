# North Carolina housing predictability

DTSC 2302 Modeling and Society, UNC Charlotte. Neelesh Reddi and Anirudh Ramesh.

We study housing affordability and whether time series forecasts of home values perform similarly across county income groups. The project includes a Mecklenburg pilot and an expanded analysis of 92 NC counties with complete development histories. Income groups use fixed 2019 ACS estimates. The final test period remains separate from development.

## Start here

1. Read [the multi-county findings](docs/PANEL_FINDINGS.md) and [the project plan](docs/PROJECT_PLAN.md).
2. Use [the initial pilot findings](docs/PILOT_FINDINGS.md) to understand the first experiment. It is a historical progress record; its ACS-pending status has since been resolved.
3. Review [the AI assistance log](AI_ASSISTANCE_LOG.md). Students must verify and understand the work before submitting it.

## Reproduce the pilot

Use Python 3.12. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/download_data.py
.\.venv\Scripts\python.exe scripts/run_pilot.py
```

The existing local `.venv` is ready to run. No environment activation is required.

The manifest records exact download URLs, access times, and SHA-256 hashes. Provider files change over time. The downloader refuses to substitute changed live data for the recorded vintage. Group members need the original raw snapshots to reproduce these exact results; transfer them through the group's shared storage. Raw data, generated outputs, and the virtual environment are excluded from Git. Keep publisher acknowledgments when sharing results.

The Census API currently requires a key. The ten income snapshots needed for the panel are already downloaded locally. A key is needed only to fetch new ACS files, not to run the offline analysis. Downloading uses the local `CENSUS_API_KEY` environment variable. Never put a key in code, notebooks, or Git. Zillow/FRED CSV downloads and local StatsForecast/MLForecast do not need additional API keys. This project does not call TimeGPT.

## Reproduce the county analysis

Once the raw snapshots are present:

```powershell
.\.venv\Scripts\python.exe scripts/run_panel.py
.\.venv\Scripts\python.exe scripts/verify_panel.py
.\.venv\Scripts\python.exe scripts/interpret_panel.py
```

To acquire the income files on another computer, set `CENSUS_API_KEY` locally and run:

```powershell
.\.venv\Scripts\python.exe scripts/download_data.py --acs-years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024
```

`run_panel.py --prepare-only` verifies inputs and fixes the cohort before fitting. `--analyze-only` rebuilds the summaries and charts from existing validation predictions. The design and data hashes must match the frozen cohort. Edit the design only as a documented new experiment, not to relabel old results.

The panel uses every county with 129 complete positive monthly ZHVI observations from January 2015 through September 2025. It evaluates 36 one-month targets per county, from October 2022 through September 2025. The ML models pool counties, while statistical models fit each county separately. This training distinction is documented in the findings. Four EDA charts and two evaluation charts are in `output/panel/`.

The verification script checks the saved targets, baseline, metrics, group summaries, and affordability ratios against original inputs. The interpretation script adds two charts, coefficient output, and paired rate-feature summaries. See [the walkthrough](docs/ANALYSIS_WALKTHROUGH.md), [interpretation notes](docs/MODEL_INTERPRETATION.md), and [new source verification notes](docs/SOURCE_VERIFICATION_ADDITIONS.md).

## GitHub Desktop

This folder is already a Git repository. Its remote is `https://github.com/nreddi2/housingpredictability.git`; the working branch is `codex/forecasting-pilot`.

In GitHub Desktop, use **File > Add Local Repository** and choose:

```text
C:\Users\nreddi\OneDrive\Documents\ChatGPT\DTSC 2302 FInal Project
```

Adding the folder to Desktop displays the existing repository; it does not create a new copy. GitHub website updates require committed changes to be pushed. GitHub Desktop's account authentication handles that separately from Census API access.

## What runs

- County coverage audit of the NC Zillow series.
- Monthly reshape, county FIPS identifiers, and monthly means of weekly mortgage rates.
- Mecklenburg pilot with a last-value baseline, drift benchmark, AutoARIMA, and three MLForecast models (Ridge, Random Forest, histogram gradient boosting).
- The three ML models run both with and without past mortgage rates.
- Twelve rolling one-month validation forecasts on October 2024 through September 2025. October 2025 through September 2026 remains reserved for final evaluation.
- MAE, RMSE, MAPE, signed errors, and four charts (two descriptive charts and two evaluation charts).

The pilot's four charts are not four EDA figures; the expanded panel supplies four EDA figures separately. Both experiments use a current revised data snapshot, so they are not fully reconstructed real-time forecasting experiments. Results are preliminary and do not establish causation or discrimination.

## Layout

- `scripts/`: download and executable analysis code.
- `data/raw/pilot_download_manifest.json`: tracked provenance and hashes.
- `data/raw/`: original datasets, excluded from Git.
- `data/processed/`: regenerated monthly datasets, excluded from Git.
- `output/pilot/`: regenerated coverage table, predictions, metrics, run metadata, and charts.
- `output/panel/`: fixed groups, eligibility, affordability comparison, county/group forecast errors, sensitivity checks, and charts.
- `config/panel_design.json`: predeclared cohort and modeling design.
- `docs/`: scope, decisions, and progress summaries.
- `requirements-lock.txt`: installed Python package versions for this run.

See the plan for source documentation and the outstanding instructor and research decisions. AI assistance must be disclosed under the course policy, which the group still needs to confirm.
