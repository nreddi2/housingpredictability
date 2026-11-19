"""Inspect the rate-using Ridge model and its saved rolling validation errors.

Coefficient fitting uses development data through September 2025 only.
It does not evaluate or forecast the final holdout.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences, LocalStandardScaler

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/panel'


def main():
    dev=pd.read_csv(ROOT/'data/processed/panel_development.csv',dtype={'unique_id':str},parse_dates=['ds'])
    assert dev.ds.max()==pd.Timestamp('2025-09-30')
    model=MLForecast(models={'Ridge_with_rates':make_pipeline(StandardScaler(),Ridge(alpha=1.0))},
                     freq='ME',lags=[1,2,3,6,12],num_threads=4,
                     target_transforms=[Differences([1]),LocalStandardScaler()])
    model.fit(dev,static_features=[])
    fitted=model.models_['Ridge_with_rates']
    names=model.ts.features_order_
    coef=fitted.named_steps['ridge'].coef_
    assert len(names)==len(coef)==7
    coefficients=pd.DataFrame({'feature':names,'standardized_coefficient':coef})
    coefficients['absolute_coefficient']=coefficients.standardized_coefficient.abs()
    coefficients=coefficients.sort_values('absolute_coefficient',ascending=False)
    coefficients.to_csv(OUT/'ridge_development_coefficients.csv',index=False)

    cv=pd.read_csv(OUT/'validation_predictions.csv',dtype={'unique_id':str},parse_dates=['ds'])
    groups=pd.read_csv(OUT/'county_groups_and_eligibility.csv',dtype={'unique_id':str})
    residual=cv[['unique_id','ds','y','Ridge_with_rates']].merge(groups[['unique_id','income_group']],on='unique_id',validate='many_to_one')
    residual['signed_error_USD']=residual.Ridge_with_rates-residual.y
    residual['signed_error_percent']=100*residual.signed_error_USD/residual.y
    residual['absolute_percentage_error']=residual.signed_error_percent.abs()
    monthly=residual.groupby(['income_group','ds']).agg(mean_signed_error_percent=('signed_error_percent','mean'),mean_APE_percent=('absolute_percentage_error','mean'),n_counties=('unique_id','size')).reset_index()
    monthly.to_csv(OUT/'ridge_group_errors_by_month.csv',index=False)
    colors={'Lower':'#a75324','Middle':'#527a9b','Higher':'#00735b'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,1,figsize=(11,7.5),sharex=True)
    for group,color in colors.items():
        a=monthly[monthly.income_group.eq(group)]
        axes[0].plot(a.ds,a.mean_signed_error_percent,color=color,label=group)
        axes[1].plot(a.ds,a.mean_APE_percent,color=color)
    axes[0].axhline(0,color='grey',linestyle='--');axes[0].legend(frameon=False)
    axes[0].set(title='Ridge with mortgage rates: validation errors over time',ylabel='Mean signed error (%)')
    axes[1].set(xlabel='Target month',ylabel='Mean absolute error (%)',xlim=(monthly.ds.min(),monthly.ds.max()))
    fig.text(.07,.015,'Equal county weights. Positive signed errors indicate overprediction. October 2022–September 2025 validation.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(OUT/'07_errors_over_time.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(figsize=(11,5.5));c=coefficients.sort_values('standardized_coefficient')
    ax.barh(c.feature,c.standardized_coefficient,color=['#a75324' if x<0 else '#00735b' for x in c.standardized_coefficient])
    ax.axvline(0,color='grey',linewidth=1)
    ax.set(title='Ridge coefficients after fitting the development panel',xlabel='Coefficient per one standard deviation of a model feature')
    fig.text(.055,.012,'Target: standardized monthly change. Fit through September 2025. Correlated features; coefficients are not causal effects.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUT/'08_ridge_coefficients.png',dpi=160);plt.close(fig)

    rates=pd.read_csv(OUT/'mortgage_feature_comparison.csv')
    rate_summary=rates.groupby('family').agg(mean_MAE_change_USD=('MAE_change_USD','mean'),median_MAE_change_USD=('MAE_change_USD','median'),fraction_counties_improved=('MAE_change_USD',lambda s:float(s.lt(0).mean()))).reset_index()
    rate_summary.to_csv(OUT/'mortgage_feature_summary.csv',index=False)
    metadata={'model':'Ridge_with_rates','fit_start':str(dev.ds.min().date()),'fit_end':str(dev.ds.max().date()),
              'n_counties':int(dev.unique_id.nunique()),'coefficient_units':'standardized target-change units per one globally standardized feature unit',
              'final_holdout_used':False,'interpretation':'descriptive conditional associations; correlated lag features prevent causal interpretation'}
    (OUT/'interpretation_metadata.json').write_text(json.dumps(metadata,indent=2))
    lines=['# Model interpretation notes','',
           'The rate-inclusive research question uses Ridge with mortgage rates as the strongest rate-using development configuration. AutoARIMA still leads the full comparison. These notes describe Ridge behavior and do not change any model choice or final-test boundary.','',
           '## Mortgage-rate feature comparison','',
           'Each row summarizes paired county differences between the same regressor with and without mortgage-rate features. Negative MAE changes mean that adding rates reduced error. The median and mean can disagree because a few counties have larger changes.','',
           '| Family | Mean MAE change ($) | Median MAE change ($) | Counties improved (%) |','|---|---:|---:|---:|']
    for r in rate_summary.itertuples():lines.append(f'| {r.family} | {r.mean_MAE_change_USD:+.2f} | {r.median_MAE_change_USD:+.2f} | {100*r.fraction_counties_improved:.1f} |')
    lines+=['','These differences provide no uniform benefit across all three families and counties. They concern these two lagged rate features and one-month forecasts; they do not establish the causal effect of rates or rule out other rate specifications.','',
            '## Coefficients','',
            'For interpretation only, Ridge was refitted on the complete development panel through September 2025. This is a single end-of-development fit, not a summary of coefficients from every rolling fold. Features and target changes are standardized as described in the walkthrough. Coefficient magnitudes are conditional on the other, correlated lag features.','',
            '| Feature | Standardized coefficient |','|---|---:|']
    for r in coefficients.itertuples():lines.append(f'| {r.feature} | {r.standardized_coefficient:+.4f} |')
    lines+=['','Do not interpret a mortgage-rate coefficient as a change in house-price dollars caused by a one-percentage-point rate change. These units describe transformed predictive associations.','',
            '## Error analysis','',
            '`output/panel/07_errors_over_time.png` shows the average signed and absolute percentage errors within each income group for every validation target. Shared error spikes may reflect common shocks or model limitations. They are not independent observations or proof of a causal mechanism. `ridge_group_errors_by_month.csv` preserves the underlying values.','',
            'The final holdout remains unused. Review the coefficient and residual patterns with the original series, measurement limits, and source literature before writing the final interpretation.']
    (ROOT/'docs/MODEL_INTERPRETATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(coefficients.to_string(index=False));print(rate_summary.round(4).to_string(index=False))


if __name__=='__main__':main()
