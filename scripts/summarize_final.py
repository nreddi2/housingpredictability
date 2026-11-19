"""Recompute published scores directly from the archived one-month forecasts."""
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / 'results' / 'final'


def save_errors(p):
    keys = ['unique_id','income_group','boundary_uncertain']
    errors = p.melt(id_vars=keys + ['ds','y'], value_vars=['Naive','Ridge_with_rates','Ridge_history_only','AutoARIMA'],
                    var_name='model', value_name='forecast')
    errors['signed'] = errors.forecast - errors.y
    errors['MAE'] = errors.signed.abs()
    errors['MSE'] = errors.signed ** 2
    errors['MAPE'] = errors.MAE / errors.y * 100
    errors[keys + ['ds','model','signed','MAPE']].rename(columns={'MAPE':'APE'}).to_csv(OUT/'forecast_errors.csv',index=False)


def summarize():
    keys = ['unique_id','income_group','boundary_uncertain']
    errors = pd.read_csv(OUT/'forecast_errors.csv').rename(columns={'APE':'MAPE'})
    assert not errors.duplicated(['unique_id','ds','model']).any()
    assert len(errors) == 92 * 12 * 4
    errors['MAE'] = errors.signed.abs()
    errors['MSE'] = errors.signed ** 2
    county = errors.groupby(keys + ['model'])[['MAE','MSE','MAPE','signed']].mean().reset_index()
    county['RMSE'] = np.sqrt(county.pop('MSE'))
    baseline = county[county.model.eq('Naive')].set_index('unique_id').MAE
    assert (baseline > 0).all()
    county['relative_MAE'] = county.MAE / county.unique_id.map(baseline)
    county.to_csv(OUT / 'county_scores.csv',index=False)
    for frame, by, file in [(county,['model'],'overall'),(county,['model','income_group'],'groups'),
                             (county[~county.boundary_uncertain],['model','income_group'],'groups_sensitivity')]:
        group = frame.groupby(by)
        result = group[['MAE','RMSE','MAPE','relative_MAE','signed']].mean()
        result['counties'] = group.size()
        result.to_csv(OUT / (file + '.csv'))
    errors[errors.model.eq('Ridge_with_rates')].groupby(['ds','income_group'])[['MAE','MAPE','signed']].mean().to_csv(OUT/'ridge_monthly.csv')


if __name__ == '__main__':
    summarize()
