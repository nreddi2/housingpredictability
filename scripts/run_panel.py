"""Income, affordability and retrospective multi-county forecasting analysis.

Run: python scripts/run_panel.py [--prepare-only | --analyze-only]
The design is recorded before fitting in config/panel_design.json.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences, LocalStandardScaler
from statsforecast import StatsForecast
from statsforecast.models import Naive, RandomWalkWithDrift, AutoARIMA

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/raw'
OUT = ROOT/'output/panel'
PROCESSED = ROOT/'data/processed'
DESIGN = json.loads((ROOT/'config/panel_design.json').read_text())
GROUPS = ['Lower', 'Middle', 'Higher']
COLORS = {'Lower': '#a75324', 'Middle': '#527a9b', 'Higher': '#00735b'}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW/'pilot_download_manifest.json').read_text())
    for item in manifest:
        assert hashlib.sha256((RAW/item['filename']).read_bytes()).hexdigest() == item['sha256']
    frames = []
    for year in range(2015, 2025):
        item = next(r for r in manifest if r['filename'].startswith(f'acs5_income_nc_{year}_'))
        a = json.loads((RAW/item['filename']).read_text())
        a = pd.DataFrame(a[1:], columns=a[0])
        a['unique_id'] = a.state + a.county
        a['county'] = a.NAME.str.replace(', North Carolina', '', regex=False)
        a['income'] = pd.to_numeric(a.B19013_001E, errors='coerce')
        a['income_moe'] = pd.to_numeric(a.B19013_001M, errors='coerce')
        a['year'] = year
        assert len(a) == 100 and a.unique_id.is_unique
        # Suppression codes are negative; retain explicit missing values, never treat as dollars.
        a.loc[a.income.le(0), 'income'] = np.nan
        a.loc[a.income_moe.lt(0), 'income_moe'] = np.nan
        frames.append(a[['unique_id','county','year','income','income_moe']])
    income = pd.concat(frames, ignore_index=True)
    assert income[['income','income_moe']].notna().all().all()
    income.to_csv(PROCESSED/'acs_income_2015_2024.csv', index=False)
    base = income[income.year.eq(2019)].drop(columns='year').rename(
        columns={'income':'income_2019', 'income_moe':'income_moe_2019'}).copy()
    # Round floating-point interpolation noise so exact-dollar boundary ties
    # follow the declared <= rule (e.g. 50558 must not become 50557.99999999).
    cuts = np.round(base.income_2019.quantile([1/3, 2/3]).to_numpy(), 6)
    base['income_group'] = np.select([base.income_2019.le(cuts[0]), base.income_2019.le(cuts[1])],
                                     ['Lower','Middle'], default='Higher')
    lo, hi = base.income_2019-base.income_moe_2019, base.income_2019+base.income_moe_2019
    base['boundary_uncertain'] = ((lo.le(cuts[0])&hi.ge(cuts[0])) | (lo.le(cuts[1])&hi.ge(cuts[1])))
    base['income_relative_moe_pct'] = 100*base.income_moe_2019/base.income_2019

    z = pd.read_csv(RAW/'zillow_county_zhvi_2026-11-01.csv')
    nc = z[z.State.eq('NC')].copy()
    nc['unique_id'] = nc.StateCodeFIPS.astype(int).astype(str).str.zfill(2)+nc.MunicipalCodeFIPS.astype(int).astype(str).str.zfill(3)
    date_cols = z.columns[z.columns.str.fullmatch(r'\d{4}-\d{2}-\d{2}')].tolist()
    # Filter columns before reshaping so the final holdout never enters this analysis.
    dates = [c for c in date_cols if DESIGN['development_start'] <= c <= DESIGN['development_end']]
    assert len(dates) == 129
    long = nc.melt(id_vars=['unique_id'], value_vars=dates, var_name='ds', value_name='y')
    long['ds'] = pd.to_datetime(long.ds)
    long = long.sort_values(['unique_id','ds']).reset_index(drop=True)
    counts = long.groupby('unique_id').agg(positive_months=('y',lambda s: int(s.gt(0).sum())))
    base = base.merge(counts, on='unique_id', validate='one_to_one')
    base['eligible'] = base.positive_months.eq(129) & base.income_2019.gt(0) & base.income_moe_2019.ge(0)
    base['exclusion_reason'] = np.where(base.eligible, '', 'Incomplete or nonpositive development ZHVI history')
    base.to_csv(OUT/'county_groups_and_eligibility.csv', index=False)
    dev = long[long.unique_id.isin(base.loc[base.eligible,'unique_id'])].copy()
    f = pd.read_csv(RAW/'mortgage30us_2026-11-01.csv')
    f['ds'] = pd.to_datetime(f.iloc[:,0]); f['rate'] = pd.to_numeric(f.MORTGAGE30US,errors='coerce')
    monthly = f.set_index('ds').rate.resample('ME').mean()
    rates = pd.DataFrame({'mortgage_rate_lag1':monthly.shift(1), 'rate_change_lag1':monthly.diff().shift(1)}).reset_index()
    dev = dev.merge(rates, on='ds', how='left', validate='many_to_one')
    assert dev.notna().all().all() and dev.y.gt(0).all()
    assert not dev.duplicated(['unique_id','ds']).any()
    np.testing.assert_allclose(dev.mortgage_rate_lag1, monthly.reindex(dev.ds-pd.offsets.MonthEnd(1)).to_numpy())
    assert dev.groupby('unique_id').size().eq(129).all()
    dev.to_csv(PROCESSED/'panel_development.csv', index=False)

    annual = dev.assign(year=dev.ds.dt.year).groupby(['unique_id','year']).agg(
        mean_zhvi=('y','mean'), n_months=('y','count')).reset_index()
    annual = annual[annual.n_months.eq(12)&annual.year.isin([2019,2024])]
    aff = annual.merge(income, on=['unique_id','year'],validate='one_to_one').merge(
        base[['unique_id','income_group']],on='unique_id',validate='many_to_one')
    aff['value_to_income'] = aff.mean_zhvi/aff.income
    aff['ratio_income_moe_lower'] = aff.mean_zhvi/(aff.income+aff.income_moe)
    aff['ratio_income_moe_upper'] = aff.mean_zhvi/(aff.income-aff.income_moe)
    assert (aff.income-aff.income_moe).gt(0).all()
    assert len(aff) == 2*base.eligible.sum()
    aff.to_csv(OUT/'affordability_2019_2024.csv',index=False)
    frozen = {'design':DESIGN,'income_cutoffs_USD':cuts.tolist(),
              'eligible_ids':sorted(base.loc[base.eligible,'unique_id'].tolist()),
              'counts_all_counties':base.groupby('income_group').size().to_dict(),
              'counts_eligible':base[base.eligible].groupby('income_group').size().to_dict(),
              'design_sha256':hashlib.sha256((ROOT/'config/panel_design.json').read_bytes()).hexdigest(),
              'source_hashes':{r['filename']:r['sha256'] for r in manifest}}
    freeze_path=OUT/'cohort_frozen_before_fitting.json'
    if freeze_path.exists():
        assert json.loads(freeze_path.read_text()) == frozen, 'Design/data changed; use a new analysis version.'
    else:
        freeze_path.write_text(json.dumps(frozen,indent=2))
    print('Eligible counties by fixed 2019 group:',frozen['counts_eligible'],flush=True)
    print('2019 income boundaries:',cuts.tolist(),flush=True)
    return dev, base, aff


def forecast(dev):
    keys=['unique_id','ds','cutoff','y']
    windows=DESIGN['validation_windows']
    print('Running county-specific StatsForecast benchmarks and AutoARIMA',flush=True)
    sf=StatsForecast(models=[Naive(),RandomWalkWithDrift(),AutoARIMA(seasonal=False,max_p=3,max_q=3)],freq='ME',n_jobs=4)
    cv=sf.cross_validation(df=dev[['unique_id','ds','y']],h=1,n_windows=windows,step_size=1,refit=True)
    cv.to_csv(OUT/'statistical_validation_predictions.csv',index=False)
    for with_rates in [False,True]:
        suffix='with_rates' if with_rates else 'history_only'
        models={
            f'Ridge_{suffix}':make_pipeline(StandardScaler(),Ridge(alpha=1.0)),
            f'RandomForest_{suffix}':RandomForestRegressor(n_estimators=200,max_depth=6,min_samples_leaf=5,random_state=2302,n_jobs=4),
            f'GradientBoosting_{suffix}':HistGradientBoostingRegressor(max_iter=150,max_leaf_nodes=10,l2_regularization=1.0,early_stopping=False,random_state=2302)}
        ml=MLForecast(models=models,freq='ME',lags=DESIGN['ml_lags'],num_threads=4,
                      target_transforms=[Differences([1]),LocalStandardScaler()])
        cols=['unique_id','ds','y']+(DESIGN['rate_features'] if with_rates else [])
        print('Running pooled MLForecast',suffix,flush=True)
        result=ml.cross_validation(df=dev[cols],h=1,n_windows=windows,step_size=1,refit=True,static_features=[])
        cv=cv.merge(result,on=keys,how='inner',validate='one_to_one')
    cv=cv.sort_values(['unique_id','ds']).reset_index(drop=True)
    assert len(cv)==dev.unique_id.nunique()*windows
    assert cv.groupby('unique_id').size().eq(windows).all()
    assert (cv.ds==cv.cutoff+pd.offsets.MonthEnd(1)).all()
    assert cv.ds.max()<=pd.Timestamp(DESIGN['development_end'])
    previous=dev.rename(columns={'ds':'cutoff','y':'previous_y'})[['unique_id','cutoff','previous_y']]
    check=cv.merge(previous,on=['unique_id','cutoff'],validate='one_to_one')
    np.testing.assert_allclose(check.Naive,check.previous_y)
    assert np.isfinite(cv.drop(columns=['unique_id','ds','cutoff']).to_numpy()).all()
    cv.to_csv(OUT/'validation_predictions.csv',index=False)
    return cv


def evaluate(cv,base):
    model_cols=[c for c in cv if c not in ['unique_id','ds','cutoff','y']]
    long=cv.melt(id_vars=['unique_id','ds','cutoff','y'],value_vars=model_cols,var_name='model',value_name='prediction')
    long['error']=long.prediction-long.y
    long['abs_error']=long.error.abs();long['sq_error']=long.error**2
    long['ape']=long.abs_error/long.y*100
    metrics=long.groupby(['unique_id','model']).agg(MAE_USD=('abs_error','mean'),MSE=('sq_error','mean'),MAPE_percent=('ape','mean'),mean_error_USD=('error','mean'),n_forecasts=('error','size')).reset_index()
    metrics['RMSE_USD']=np.sqrt(metrics.pop('MSE'))
    naive=metrics[metrics.model.eq('Naive')][['unique_id','MAE_USD']].rename(columns={'MAE_USD':'naive_MAE_USD'})
    metrics=metrics.merge(naive,on='unique_id',validate='many_to_one')
    assert metrics.naive_MAE_USD.gt(0).all()
    metrics['relative_MAE']=metrics.MAE_USD/metrics.naive_MAE_USD
    metrics['beats_naive']=metrics.relative_MAE.lt(1)
    metrics=metrics.merge(base[['unique_id','county','income_group','income_2019','boundary_uncertain']],on='unique_id',validate='many_to_one')
    metrics.to_csv(OUT/'county_metrics.csv',index=False)
    groups=metrics.groupby(['model','income_group']).agg(n_counties=('unique_id','size'),mean_county_MAE_USD=('MAE_USD','mean'),mean_county_RMSE_USD=('RMSE_USD','mean'),mean_county_MAPE_percent=('MAPE_percent','mean'),mean_relative_MAE=('relative_MAE','mean'),median_relative_MAE=('relative_MAE','median'),fraction_beating_naive=('beats_naive','mean')).reset_index()
    groups.to_csv(OUT/'income_group_metrics.csv',index=False)
    overall=metrics.groupby('model').agg(n_counties=('unique_id','size'),mean_county_MAE_USD=('MAE_USD','mean'),mean_county_RMSE_USD=('RMSE_USD','mean'),mean_county_MAPE_percent=('MAPE_percent','mean'),mean_relative_MAE=('relative_MAE','mean'),fraction_beating_naive=('beats_naive','mean')).sort_values('mean_relative_MAE').reset_index()
    overall.to_csv(OUT/'overall_metrics.csv',index=False)
    stable=metrics[~metrics.boundary_uncertain]
    sensitivity=stable.groupby(['model','income_group']).agg(n_counties=('unique_id','size'),mean_county_MAPE_percent=('MAPE_percent','mean'),mean_relative_MAE=('relative_MAE','mean')).reset_index()
    sensitivity.to_csv(OUT/'income_boundary_sensitivity.csv',index=False)
    # Rate-feature comparisons are paired within each county and regressor.
    paired=[]
    for family in ['Ridge','RandomForest','GradientBoosting']:
        h=metrics[metrics.model.eq(family+'_history_only')]
        r=metrics[metrics.model.eq(family+'_with_rates')]
        x=h[['unique_id','county','income_group','MAE_USD','MAPE_percent']].merge(r[['unique_id','MAE_USD','MAPE_percent']],on='unique_id',suffixes=('_history','_rates'),validate='one_to_one')
        x['family']=family;x['MAE_change_USD']=x.MAE_USD_rates-x.MAE_USD_history
        x['MAPE_change_percentage_points']=x.MAPE_percent_rates-x.MAPE_percent_history
        paired.append(x)
    pd.concat(paired).to_csv(OUT/'mortgage_feature_comparison.csv',index=False)
    return metrics,groups,overall,sensitivity


def figures(dev,base,aff,metrics,groups,overall):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name,caption):
        fig.text(.06,.012,caption,fontsize=9)
        fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUT/name,dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5.5))
    for group in GROUPS:
        a=base[base.income_group.eq(group)]
        ax.scatter(a.income_2019,a.income_relative_moe_pct,label=group,color=COLORS[group],alpha=.8,s=30)
    ax.set(xlabel='2019 ACS median household income (2019 USD)',ylabel='Income margin of error / estimate (%)',title='Income estimates vary in precision across NC counties')
    ax.xaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'));ax.legend(title='Fixed 2019 income third',frameon=False)
    save(fig,'01_income_measurement.png','All 100 NC counties. ACS 2015–2019 estimates; margins of error are published by Census.')

    indexed=dev.copy();indexed['indexed_y']=indexed.y/indexed.groupby('unique_id').y.transform('first')*100
    indexed=indexed.merge(base[['unique_id','income_group']],on='unique_id',validate='many_to_one')
    agg=indexed.groupby(['income_group','ds']).indexed_y.agg(['median',lambda s:s.quantile(.25),lambda s:s.quantile(.75)]).reset_index()
    agg.columns=['income_group','ds','median','q25','q75']
    fig,ax=plt.subplots(figsize=(11,5.5))
    for group in GROUPS:
        a=agg[agg.income_group.eq(group)];ax.plot(a.ds,a['median'],label=group,color=COLORS[group]);ax.fill_between(a.ds,a.q25,a.q75,color=COLORS[group],alpha=.1)
    ax.set(title='Home-value paths by fixed county income group',xlabel='Month',ylabel='ZHVI indexed to January 2015 = 100');ax.legend(frameon=False)
    ax.set_xlim(dev.ds.min(),dev.ds.max())
    save(fig,'02_indexed_home_values.png','Eligible counties; group medians and interquartile ranges. Zillow smoothed, adjusted series. Development data only.')

    fig,ax=plt.subplots(figsize=(11,5.5))
    for i,group in enumerate(GROUPS):
        a=aff[aff.income_group.eq(group)].pivot(index='unique_id',columns='year',values='value_to_income')
        for _,row in a.iterrows():ax.plot([i-.18,i+.18],row[[2019,2024]],color=COLORS[group],alpha=.22,linewidth=.8)
        ax.scatter(np.repeat(i-.18,len(a)),a[2019],color=COLORS[group],s=15,alpha=.65)
        ax.scatter(np.repeat(i+.18,len(a)),a[2024],color=COLORS[group],marker='x',s=18,alpha=.7)
        ax.plot([i-.18,i+.18],a[[2019,2024]].median(),color='black',linewidth=3,marker='o')
    ax.set(xticks=range(3),xticklabels=GROUPS,xlabel='Fixed 2019 income group',ylabel='Annual mean ZHVI / household income',title='Home-value-to-income proxy in 2019 and 2024')
    ax.text(.01,.98,'Left: 2019   Right: 2024\nBlack: county median',transform=ax.transAxes,va='top',fontsize=10)
    save(fig,'03_affordability_comparison.png','Income periods: 2015–2019 and 2020–2024. Endpoint home values / period income; not household payment burden.')

    changes=dev.copy();changes['pct_change']=changes.groupby('unique_id').y.pct_change()*100
    changes=changes.merge(base[['unique_id','income_group']],on='unique_id',validate='many_to_one')
    volatility=changes.groupby(['unique_id','income_group'])['pct_change'].std().reset_index()
    fig,ax=plt.subplots(figsize=(11,5.5));rng=np.random.default_rng(2302)
    for i,group in enumerate(GROUPS):
        values=volatility.loc[volatility.income_group.eq(group),'pct_change']
        ax.scatter(i+rng.uniform(-.13,.13,len(values)),values,color=COLORS[group],alpha=.7)
        ax.plot([i-.18,i+.18],[values.median()]*2,color='black',linewidth=3)
    ax.set(xticks=range(3),xticklabels=GROUPS,xlabel='Fixed 2019 income group',ylabel='SD of monthly ZHVI percentage change',title='County home-value volatility differs within income groups')
    save(fig,'04_county_volatility.png','One point per county, January 2015–September 2025. Black lines show medians; smoothed index variability.')

    fig,ax=plt.subplots(figsize=(11,6))
    m=overall.iloc[::-1];labels=m.model.str.replace('_history_only',' (history)').str.replace('_with_rates',' (+ rates)')
    ax.barh(labels,m.mean_relative_MAE,color=['#888888' if n=='Naive' else '#00735b' for n in m.model]);ax.axvline(1,color='black',linestyle='--')
    ax.set(title='Average county error relative to the last-value baseline',xlabel='Mean of county MAE / county naive MAE')
    save(fig,'05_model_comparison.png','36 rolling one-month targets per county, Oct 2022–Sep 2025. Equal county weights. Below 1 beats the baseline.')

    best=overall.model.iloc[0]
    # Display the strongest rate-using configuration to address the research
    # question directly, alongside the all-model ranking in the prior figure.
    rate_best=overall.loc[overall.model.str.endswith('_with_rates'),'model'].iloc[0]
    fig,axes=plt.subplots(1,2,figsize=(12,5.5));rng=np.random.default_rng(2302)
    for ax,col,label in zip(axes,['MAPE_percent','relative_MAE'],['County MAPE (%)','County MAE / naive MAE']):
        for i,group in enumerate(GROUPS):
            v=metrics.loc[metrics.model.eq(rate_best)&metrics.income_group.eq(group),col]
            ax.scatter(i+rng.uniform(-.13,.13,len(v)),v,color=COLORS[group],alpha=.7,s=25);ax.plot([i-.18,i+.18],[v.median()]*2,color='black',linewidth=3)
        ax.set(xticks=range(3),xticklabels=GROUPS,ylabel=label)
    axes[1].axhline(1,color='grey',linestyle='--');fig.suptitle(f'County errors by income group: {rate_best}')
    save(fig,'06_income_group_errors.png','Oct 2022–Sep 2025. One point per county; black lines show medians. Descriptive results, not a discrimination test.')
    return best


def report(dev,base,aff,metrics,groups,overall,sensitivity,best,elapsed):
    eligible=base[base.eligible]
    selected=groups[groups.model.eq(best)].set_index('income_group').reindex(GROUPS)
    rate_best=overall.loc[overall.model.str.endswith('_with_rates'),'model'].iloc[0]
    rate_selected=groups[groups.model.eq(rate_best)].set_index('income_group').reindex(GROUPS)
    affsummary=aff.groupby(['income_group','year']).value_to_income.median().unstack()
    summary={'eligible_counties':len(eligible),'excluded_counties':base.loc[~base.eligible,'county'].tolist(),
             'group_counts':eligible.groupby('income_group').size().to_dict(),
             'validation_start':'2022-10-31','validation_end':'2025-09-30',
             'forecasts_per_model':len(eligible)*36,'final_holdout_evaluated':False,
             'best_development_model_by_mean_relative_MAE':best,
             'best_rate_using_model_by_mean_relative_MAE':rate_best,
             'current_invocation_elapsed_seconds':round(elapsed,1),
             'boundary_uncertain_eligible_count':int(eligible.boundary_uncertain.sum())}
    (OUT/'run_summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# Multi-county development findings','',
           'Executed November 1, 2026. All results are preliminary development results. The final October 2025–September 2026 holdout remains unevaluated.','',
           '## Data and cohort','',
           f'Census income estimates and margins of error cover 100 NC counties in each 2015–2024 ACS five-year release. {len(eligible)} counties meet the predeclared requirement of 129 complete, positive monthly ZHVI values from January 2015 through September 2025. All eligible counties are included; none were selected by forecast performance.','',
           'Income groups use fixed 2019 estimates ranked across all 100 counties. This represents the 2015–2019 income period, not a single-year survey. Eligibility uses development data only. Excluded counties: '+', '.join(summary['excluded_counties'])+'.','',
           '## Modeling design','',
           'Each model predicts the next month at 36 expanding training cutoffs, giving '+str(summary['forecasts_per_model'])+' county-month forecasts per model from October 2022 through September 2025. Statistical models fit separately to each county. ML models pool counties, with county-specific differencing and standardization fitted anew within each training window. No income group is a predictor. Mortgage features use the preceding month.','',
           'This differs from the Mecklenburg pilot in its common start date, longer validation interval, pooled ML training, and target standardization. The results are not an apples-to-apples comparison with the pilot. Pooled ML also has access to other counties\' training histories, unlike the local statistical models.','',
           'The predeclared selection metric is the equal-county mean of model MAE divided by that county\'s naive MAE. A value below 1 indicates lower average relative error. This avoids selecting only on dollar errors dominated by more expensive markets.','',
           '| Model | Mean relative MAE | Mean county MAE ($) | Mean county MAPE (%) | Counties beating naive (%) |',
           '|---|---:|---:|---:|---:|']
    for r in overall.itertuples():lines.append(f'| {r.model} | {r.mean_relative_MAE:.3f} | {r.mean_county_MAE_USD:,.2f} | {r.mean_county_MAPE_percent:.3f} | {r.fraction_beating_naive*100:.1f} |')
    lines+=['','## Income-group error comparison','',f'The development leader by the predeclared metric is {best}. Its group results follow. These are equal-county averages, not population-weighted household outcomes.','',
            '| 2019 income group | Counties | Mean county MAE ($) | Mean county RMSE ($) | Mean county MAPE (%) | Mean relative MAE |',
            '|---|---:|---:|---:|---:|---:|']
    for g,r in selected.iterrows():lines.append(f'| {g} | {int(r.n_counties)} | {r.mean_county_MAE_USD:,.2f} | {r.mean_county_RMSE_USD:,.2f} | {r.mean_county_MAPE_percent:.3f} | {r.mean_relative_MAE:.3f} |')
    gap=selected.loc['Lower','mean_county_MAPE_percent']-selected.loc['Higher','mean_county_MAPE_percent']
    lines+=['',f'The lower-minus-higher MAPE difference is {gap:+.3f} percentage points. This is a descriptive difference over these counties and dates, not evidence of discrimination or a causal income effect. Counties share economic shocks and are not independent random observations. No significance claim is made.','',
            f'{summary["boundary_uncertain_eligible_count"]} eligible counties have estimate-plus/minus-MOE intervals crossing a fixed income boundary. `income_boundary_sensitivity.csv` repeats the group summaries after excluding these counties. This is a sensitivity check, not a confidence interval for group membership: the boundary estimates also have uncertainty.','',
            '## Affordability proxy','',
            'The main comparison uses non-overlapping ACS periods: 2015–2019 and 2020–2024. Annual average 2019 and 2024 ZHVI values are divided by each corresponding end-year-dollar income estimate. This is an endpoint home-value-to-income proxy with different price/income observation windows. It is not a five-year average price ratio, a household payment measure, or a literal median-house-price ratio. Ratios are dimensionless; each numerator/denominator uses its own end-year dollar basis.','',
            '| Fixed income group | Median county ratio in 2019 | Median county ratio in 2024 |',
            '|---|---:|---:|']
    for g in GROUPS:lines.append(f'| {g} | {affsummary.loc[g,2019]:.2f} | {affsummary.loc[g,2024]:.2f} |')
    lines+=['','The affordability table includes sensitivity bounds using income estimate ± MOE. These reflect income uncertainty only; they are not complete confidence intervals for affordability because ZHVI uncertainty is not quantified. Annual ACS releases between the endpoints are retained for provenance, not treated as independent annual change measurements.']
    lines+=['','## Direct answer for a model that uses mortgage rates','',
            f'{rate_best} leads the rate-using configurations under the same relative-MAE criterion. Its comparison addresses the rate-inclusive research question; the overall leader {best} does not use rates. This is a development-model choice, not a final-test conclusion.','',
            '| Fixed income group | Counties | Mean county MAE ($) | Mean county MAPE (%) | Mean relative MAE |',
            '|---|---:|---:|---:|---:|']
    for g,r in rate_selected.iterrows():lines.append(f'| {g} | {int(r.n_counties)} | {r.mean_county_MAE_USD:,.2f} | {r.mean_county_MAPE_percent:.3f} | {r.mean_relative_MAE:.3f} |')
    rate_gap=rate_selected.loc['Lower','mean_county_MAPE_percent']-rate_selected.loc['Higher','mean_county_MAPE_percent']
    lines+=['',f'Its lower-minus-higher MAPE gap is {rate_gap:+.3f} percentage points. The group means differ descriptively. We have not established statistical significance, discrimination, or a causal explanation for the difference. Dollar errors and relative-to-baseline errors must be considered alongside MAPE.','']
    lines+=['After excluding counties whose income estimate ± MOE crosses a fixed boundary:','',
            '| Fixed income group | Retained counties | Mean county MAPE (%) | Mean relative MAE |','|---|---:|---:|---:|']
    stable=sensitivity[sensitivity.model.eq(rate_best)].set_index('income_group').reindex(GROUPS)
    for g,r in stable.iterrows():lines.append(f'| {g} | {int(r.n_counties)} | {r.mean_county_MAPE_percent:.3f} | {r.mean_relative_MAE:.3f} |')
    lines+=['','This sensitivity analysis changes the population being summarized and leaves few middle-income counties. Treat it as a robustness description, not a corrected estimate of group fairness.','',
            '## Limits and next steps','',
            '- Zillow values are smoothed, seasonally adjusted, and retrospectively revised. Observation-date splitting does not reconstruct historical publication times or real-time data vintages.',
            '- One-month forecasts do not establish performance at six or twelve months.',
            '- Group-level results do not describe individuals, establish causation, or identify discrimination.',
            '- Common-history exclusions can change which counties the study represents. Report exclusions and group counts.',
            '- Compare history-only and rate-feature models using the paired county table before attributing any forecasting benefit to rates.',
            '- Review these development results, select robustness checks, and freeze the full design before opening the final holdout.',
            '- At least ten peer-reviewed sources, instructor decisions, and human review remain required.','',
            '## Reproduction and source records','',
            '`python scripts/run_panel.py` regenerates the analysis. The design is in `config/panel_design.json`; the frozen cohort and raw-data hashes are in `output/panel/cohort_frozen_before_fitting.json`. `--prepare-only` stops before training, and `--analyze-only` rebuilds tables/figures from saved predictions.','',
            'Source documentation: https://www.zillow.com/research/data/ ; https://fred.stlouisfed.org/series/MORTGAGE30US ; https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html ; https://api.census.gov/data/2019/acs/acs5/variables/B19013_001E.json . Accessed November 1, 2026. Exact source URLs without credentials and file hashes are in the raw-data manifest.','',
            'AI assistance: Codex implemented and executed this analysis, drafted the explanations, and generated the figures. Students must review, understand, and verify the work and disclose assistance according to course policy.']
    (ROOT/'docs/PANEL_FINDINGS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(overall.round(4).to_string(index=False),flush=True)
    print(json.dumps(summary,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--prepare-only',action='store_true');mode.add_argument('--analyze-only',action='store_true')
    args=parser.parse_args();start=time.monotonic()
    dev,base,aff=prepare()
    if args.prepare_only:return
    if args.analyze_only:
        cv=pd.read_csv(OUT/'validation_predictions.csv',dtype={'unique_id':str},parse_dates=['ds','cutoff'])
    else:cv=forecast(dev)
    metrics,groups,overall,sensitivity=evaluate(cv,base)
    best=figures(dev,base,aff,metrics,groups,overall)
    report(dev,base,aff,metrics,groups,overall,sensitivity,best,time.monotonic()-start)


if __name__=='__main__':main()
