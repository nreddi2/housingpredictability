"""Reproduce the reserved-year forecasts from the group's November 1 snapshots."""

import numpy as np
import pandas as pd
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences, LocalStandardScaler
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, Naive

from run_panel import DESIGN, RAW, ROOT, prepare

RESULTS = ROOT / 'results' / 'final'
KEYS = ['unique_id', 'ds', 'cutoff', 'y']


def extend_panel(dev):
    z = pd.read_csv(RAW / 'zillow_county_zhvi_2026-11-01.csv')
    z = z.loc[z.State.eq('NC')].copy()
    z['unique_id'] = z.StateCodeFIPS.astype(str).str.zfill(2) + z.MunicipalCodeFIPS.astype(str).str.zfill(3)
    dates = pd.date_range(DESIGN['final_holdout_start'], DESIGN['final_holdout_end'], freq='ME')
    targets = z[z.unique_id.isin(dev.unique_id)].melt(
        id_vars='unique_id', value_vars=dates.strftime('%Y-%m-%d').tolist(), var_name='ds', value_name='y')
    targets['ds'] = pd.to_datetime(targets.ds)
    weekly = pd.read_csv(RAW / 'mortgage30us_2026-11-01.csv', index_col=0, parse_dates=True)
    monthly = pd.to_numeric(weekly.MORTGAGE30US, errors='coerce').resample('ME').mean()
    previous = targets.ds - pd.offsets.MonthEnd()
    targets['mortgage_rate_lag1'] = previous.map(monthly)
    targets['rate_change_lag1'] = previous.map(monthly.diff())
    assert len(targets) == 92 * 12 and targets.notna().all().all() and targets.y.gt(0).all()
    assert not targets.duplicated(['unique_id', 'ds']).any()
    return pd.concat([dev, targets], ignore_index=True).sort_values(['unique_id','ds'])


def forecast(panel):
    cv_args = dict(h=1, n_windows=12, step_size=1, refit=True)
    history = ['unique_id', 'ds', 'y']
    sf = StatsForecast(models=[Naive(), AutoARIMA(seasonal=False, max_p=3, max_q=3)], freq='ME', n_jobs=4)
    predictions = sf.cross_validation(df=panel[history], **cv_args)
    for name, features in [('Ridge_history_only', []), ('Ridge_with_rates', DESIGN['rate_features'])]:
        ml = MLForecast(models={name: make_pipeline(StandardScaler(), Ridge(alpha=1.0))},
                        freq='ME', lags=DESIGN['ml_lags'], num_threads=4,
                        target_transforms=[Differences([1]), LocalStandardScaler()])
        result = ml.cross_validation(df=panel[history + features], static_features=[], **cv_args)
        predictions = predictions.merge(result, on=KEYS, validate='one_to_one')
    assert len(predictions) == 1104 and predictions.groupby('unique_id').size().eq(12).all()
    assert predictions.ds.min() == pd.Timestamp(DESIGN['final_holdout_start'])
    assert predictions.ds.max() == pd.Timestamp(DESIGN['final_holdout_end'])
    assert predictions.ds.eq(predictions.cutoff + pd.offsets.MonthEnd()).all()
    truth = panel.set_index(['unique_id','ds']).y
    for date_col, column in [('cutoff', 'Naive'), ('ds','y')]:
        keys = pd.MultiIndex.from_arrays([predictions.unique_id, predictions[date_col]])
        np.testing.assert_allclose(truth.reindex(keys), predictions[column])
    assert np.isfinite(predictions.drop(columns=['unique_id','ds','cutoff']).to_numpy()).all()
    return predictions


def main():
    dev, base, aff = prepare()
    predictions = forecast(extend_panel(dev))
    RESULTS.mkdir(exist_ok=True, parents=True)
    predictions = predictions.merge(base[['unique_id','income_group','boundary_uncertain']],on='unique_id',
                      validate='many_to_one')
    local = ROOT / 'output' / 'final'
    local.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(local / 'predictions.csv', index=False)
    from summarize_final import save_errors, summarize
    save_errors(predictions)
    summarize()


if __name__ == '__main__':
    main()
