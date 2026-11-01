"""Reproducible, retrospective Mecklenburg forecasting pilot.

Run from the repository root: python scripts/run_pilot.py
Uses an immutable local snapshot. No data are fetched by this script.
The final twelve observations never enter development fitting or evaluation.
"""
from pathlib import Path
import hashlib
import json
import platform
from importlib.metadata import version

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences
from statsforecast import StatsForecast
from statsforecast.models import Naive, RandomWalkWithDrift, AutoARIMA

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "output/pilot"
PROCESSED = ROOT / "data/processed"
HOLDOUT = 12
N_WINDOWS = 12
SEED = 2302


def prepare():
    manifest = json.loads((RAW / "pilot_download_manifest.json").read_text())
    for item in manifest:
        actual = hashlib.sha256((RAW / item["filename"]).read_bytes()).hexdigest()
        assert actual == item["sha256"], f"Raw data changed: {item['filename']}"
    z = pd.read_csv(RAW / "zillow_county_zhvi_2026-11-01.csv")
    nc = z.loc[z.State.eq("NC")].copy()
    dates = z.columns[z.columns.str.fullmatch(r"\d{4}-\d{2}-\d{2}")].tolist()
    nc["unique_id"] = (nc.StateCodeFIPS.astype(int).astype(str).str.zfill(2)
                       + nc.MunicipalCodeFIPS.astype(int).astype(str).str.zfill(3))
    assert nc.unique_id.is_unique
    long = nc.melt(id_vars=["unique_id", "RegionName"], value_vars=dates,
                   var_name="ds", value_name="y")
    long["ds"] = pd.to_datetime(long.ds)
    long = long.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    assert not long.duplicated(["unique_id", "ds"]).any()
    rows = []
    for uid, g in long.groupby("unique_id"):
        valid = g.dropna(subset=["y"])
        first, last = valid.ds.min(), valid.ds.max()
        interior = g.loc[g.ds.between(first, last)]
        rows.append({"unique_id": uid, "county": g.RegionName.iloc[0],
                     "first_month": first, "last_month": last,
                     "observed_months": len(valid), "missing_total": int(g.y.isna().sum()),
                     "missing_between_first_last": int(interior.y.isna().sum())})
    coverage = pd.DataFrame(rows)
    coverage.to_csv(OUT / "nc_county_coverage.csv", index=False)
    long.to_csv(PROCESSED / "nc_zhvi_monthly.csv", index=False)

    f = pd.read_csv(RAW / "mortgage30us_2026-11-01.csv")
    f["ds"] = pd.to_datetime(f.iloc[:, 0])
    f["rate"] = pd.to_numeric(f.MORTGAGE30US, errors="coerce")
    monthly = f.set_index("ds").rate.resample("ME").mean().rename("mortgage_rate").to_frame()
    # At target month t, this feature contains only month t-1's rate.
    monthly["mortgage_rate_lag1"] = monthly.mortgage_rate.shift(1)
    monthly["rate_change_lag1"] = monthly.mortgage_rate.diff().shift(1)
    monthly = monthly.reset_index()
    pilot = long.loc[long.unique_id.eq("37119"), ["unique_id", "ds", "y"]].copy()
    pilot = pilot.merge(monthly, on="ds", how="left", validate="one_to_one")
    assert pilot.y.notna().all() and (pilot.y > 0).all()
    assert pilot.ds.tolist() == pd.date_range(pilot.ds.min(), pilot.ds.max(), freq="ME").tolist()
    assert pilot[["mortgage_rate_lag1", "rate_change_lag1"]].notna().all().all()
    # Explicitly verify rate alignment rather than trusting the column name.
    rate_lookup = monthly.set_index("ds").mortgage_rate
    expected = [rate_lookup.loc[d - pd.offsets.MonthEnd(1)] for d in pilot.ds]
    np.testing.assert_allclose(pilot.mortgage_rate_lag1, expected)
    pilot.to_csv(PROCESSED / "mecklenburg_monthly.csv", index=False)
    return pilot, coverage


def model_comparison(dev):
    keys = ["unique_id", "ds", "cutoff", "y"]
    sf = StatsForecast(models=[Naive(), RandomWalkWithDrift(),
                              AutoARIMA(seasonal=False, max_p=3, max_q=3)],
                       freq="ME", n_jobs=1)
    print("Running StatsForecast rolling validation", flush=True)
    cv = sf.cross_validation(df=dev[["unique_id", "ds", "y"]],
                             h=1, n_windows=N_WINDOWS, step_size=1, refit=True)
    for with_rates in [False, True]:
        suffix = "with_rates" if with_rates else "history_only"
        models = {
            f"Ridge_{suffix}": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
            f"RandomForest_{suffix}": RandomForestRegressor(
                n_estimators=200, max_depth=6, min_samples_leaf=5,
                random_state=SEED, n_jobs=1),
            f"GradientBoosting_{suffix}": HistGradientBoostingRegressor(
                max_iter=150, max_leaf_nodes=10, l2_regularization=1.0,
                early_stopping=False, random_state=SEED),
        }
        # Model changes, then invert to dollar levels for all evaluation metrics.
        ml = MLForecast(models=models, freq="ME", lags=[1, 2, 3, 6, 12],
                        target_transforms=[Differences([1])], num_threads=1)
        cols = ["unique_id", "ds", "y"]
        if with_rates:
            cols += ["mortgage_rate_lag1", "rate_change_lag1"]
        print(f"Running MLForecast {suffix}", flush=True)
        result = ml.cross_validation(df=dev[cols], n_windows=N_WINDOWS,
                                     h=1, step_size=1, refit=True, static_features=[])
        cv = cv.merge(result, on=keys, how="inner", validate="one_to_one")
    cv = cv.sort_values("ds")
    assert len(cv) == N_WINDOWS
    assert (cv.cutoff < cv.ds).all()
    assert (cv.ds == cv.cutoff + pd.offsets.MonthEnd(1)).all()
    assert cv.ds.max() == dev.ds.max()
    # A manual persistence forecast checks the library's baseline alignment.
    expected = dev.set_index("ds").y.reindex(cv.cutoff).to_numpy()
    np.testing.assert_allclose(cv.Naive, expected)
    model_cols = [c for c in cv if c not in keys]
    assert np.isfinite(cv[model_cols].to_numpy()).all()
    metrics = []
    for name in model_cols:
        error = cv[name] - cv.y
        metrics.append({"model": name, "n_forecasts": len(error),
                        "MAE_USD": float(np.abs(error).mean()),
                        "RMSE_USD": float(np.sqrt(np.mean(error ** 2))),
                        "MAPE_percent": float((np.abs(error) / cv.y).mean() * 100),
                        "mean_error_USD": float(error.mean())})
    metrics = pd.DataFrame(metrics)
    naive_mae = metrics.loc[metrics.model.eq("Naive"), "MAE_USD"].iloc[0]
    metrics["MAE_improvement_vs_naive_percent"] = (1 - metrics.MAE_USD / naive_mae) * 100
    metrics = metrics.sort_values("MAE_USD").reset_index(drop=True)
    cv.to_csv(OUT / "validation_predictions.csv", index=False)
    metrics.to_csv(OUT / "validation_metrics.csv", index=False)
    return cv, metrics


def figures(dev, cv, metrics):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(dev.ds, dev.y, color="#006b54", linewidth=2)
    ax.set(title="Mecklenburg County typical home value", xlabel="Month", ylabel="ZHVI (USD)")
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.grid(axis="y", alpha=.2)
    fig.text(.09, .01, "Source: Zillow, downloaded Nov 1, 2026. Development period only; smoothed and seasonally adjusted.", fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT / "01_home_values.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(dev.ds, dev.mortgage_rate, color="#5666a3", linewidth=2)
    ax.set(title="National 30-year fixed mortgage rate", xlabel="Month", ylabel="Monthly mean rate (%)")
    ax.axvline(pd.Timestamp("2022-11-17"), color="#9e5a36", linestyle="--", label="Nov 2022 methodology change")
    ax.legend(frameon=False); ax.grid(axis="y", alpha=.2)
    fig.text(.09,.01,"Source: Freddie Mac via FRED. Monthly mean of weekly observations; development period only.",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT / "02_mortgage_rates.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    m = metrics.sort_values("MAE_USD", ascending=False)
    labels = m.model.str.replace("_history_only", " (history)").str.replace("_with_rates", " (+ rates)")
    colors = ["#888888" if n == "Naive" else "#006b54" for n in m.model]
    ax.barh(labels, m.MAE_USD, color=colors)
    ax.set(title="Pilot validation error across 12 one-month forecasts", xlabel="Mean absolute error (USD)")
    ax.xaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.grid(axis="x", alpha=.2)
    fig.text(.02,.01,"Earlier development windows only. Latest 12 months reserved for final testing. Lower error is better.",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT / "03_model_comparison.png", dpi=180); plt.close(fig)

    best = metrics.model.iloc[0]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(cv.ds, cv.y, color="#222222", marker="o", label="Observed")
    ax.plot(cv.ds, cv.Naive, color="#aaaaaa", linestyle="--", label="Last-value baseline")
    ax.plot(cv.ds, cv[best], color="#006b54", marker=".", label=best)
    ax.set(title="Rolling forecasts on the development validation period", xlabel="Target month", ylabel="ZHVI (USD)")
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.legend(frameon=False, fontsize=10); ax.grid(axis="y", alpha=.2)
    fig.text(.07,.01,"Best model on these validation windows, not a final-test winner. Retrospective evaluation of revised data.",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT / "04_validation_forecasts.png", dpi=180); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True)
    pilot, coverage = prepare()
    dev, holdout = pilot.iloc[:-HOLDOUT].copy(), pilot.iloc[-HOLDOUT:].copy()
    assert dev.ds.max() < holdout.ds.min()
    cv, metrics = model_comparison(dev)
    figures(dev, cv, metrics)
    summary = {
        "county": "Mecklenburg County, NC", "fips": "37119",
        "observations": len(pilot), "first_month": str(pilot.ds.min().date()),
        "last_month": str(pilot.ds.max().date()), "nc_counties_in_file": len(coverage),
        "development_end": str(dev.ds.max().date()),
        "validation_start": str(cv.ds.min().date()), "validation_end": str(cv.ds.max().date()),
        "final_holdout_start": str(holdout.ds.min().date()),
        "final_holdout_end": str(holdout.ds.max().date()), "final_holdout_evaluated": False,
        "validation_winner_by_MAE": metrics.model.iloc[0],
        "validation_winner_MAE_USD": float(metrics.MAE_USD.iloc[0]),
        "python": platform.python_version(),
        "versions": {p: version(p) for p in ["pandas", "numpy", "scikit-learn", "statsforecast", "mlforecast", "matplotlib"]},
        "limitations": ["Single county and 12 validation targets", "No income-group results yet",
                        "Current revised snapshot, not archived real-time vintages",
                        "Forecast origins use observation dates, not verified historical release dates",
                        "One-month horizon; no evidence yet about 6-12 month forecasts",
                        "No causal inference about mortgage rates"]
    }
    (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2))
    print(metrics.round(3).to_string(index=False), flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
