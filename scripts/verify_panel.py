"""Check saved panel results against raw inputs and independently recomputed scores."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'output/panel'


def main():
    manifest=json.loads((RAW/'pilot_download_manifest.json').read_text())
    for item in manifest:
        assert 'key=' not in item['url'].lower()
        assert hashlib.sha256((RAW/item['filename']).read_bytes()).hexdigest()==item['sha256']
    cv=pd.read_csv(OUT/'validation_predictions.csv',dtype={'unique_id':str},parse_dates=['ds','cutoff'])
    groups=pd.read_csv(OUT/'county_groups_and_eligibility.csv',dtype={'unique_id':str})
    saved=pd.read_csv(OUT/'county_metrics.csv',dtype={'unique_id':str}).set_index(['unique_id','model'])
    eligible=set(groups.loc[groups.eligible,'unique_id'])
    assert set(cv.unique_id)==eligible and len(eligible)==92
    expected=pd.date_range('2022-10-31','2025-09-30',freq='ME')
    for _,g in cv.groupby('unique_id'):
        assert g.ds.tolist()==expected.tolist()
    assert (cv.cutoff+pd.offsets.MonthEnd(1)==cv.ds).all()
    assert cv.ds.max()<pd.Timestamp('2025-10-01')
    models=[c for c in cv if c not in ['unique_id','ds','cutoff','y']]
    assert len(models)==9 and np.isfinite(cv[models].to_numpy()).all()

    raw=pd.read_csv(RAW/'zillow_county_zhvi_2026-11-01.csv')
    raw['unique_id']=raw.StateCodeFIPS.astype(int).astype(str).str.zfill(2)+raw.MunicipalCodeFIPS.astype(int).astype(str).str.zfill(3)
    raw=raw[raw.State.eq('NC')].set_index('unique_id')
    actual=np.array([raw.loc[r.unique_id,r.ds.strftime('%Y-%m-%d')] for r in cv.itertuples()])
    naive=np.array([raw.loc[r.unique_id,r.cutoff.strftime('%Y-%m-%d')] for r in cv.itertuples()])
    np.testing.assert_allclose(cv.y,actual)
    np.testing.assert_allclose(cv.Naive,naive)
    for uid,g in cv.groupby('unique_id'):
        denom=np.abs(g.Naive-g.y).mean()
        for model in models:
            e=g[model].to_numpy()-g.y.to_numpy(); row=saved.loc[(uid,model)]
            np.testing.assert_allclose([row.MAE_USD,row.RMSE_USD,row.MAPE_percent,row.relative_MAE],
                                      [np.mean(np.abs(e)),np.sqrt(np.mean(e**2)),np.mean(np.abs(e)/g.y)*100,np.mean(np.abs(e))/denom])
    grouped=pd.read_csv(OUT/'income_group_metrics.csv').set_index(['model','income_group'])
    for (model,group),g in saved.reset_index().groupby(['model','income_group']):
        r=grouped.loc[(model,group)]
        assert r.n_counties==len(g)
        np.testing.assert_allclose([r.mean_county_MAE_USD,r.mean_county_RMSE_USD,r.mean_county_MAPE_percent,r.mean_relative_MAE],
                                  [g.MAE_USD.mean(),g.RMSE_USD.mean(),g.MAPE_percent.mean(),g.relative_MAE.mean()])

    a=pd.read_csv(OUT/'affordability_2019_2024.csv',dtype={'unique_id':str})
    for row in a.itertuples():
        income_item=next(r for r in manifest if r['filename'].startswith(f'acs5_income_nc_{row.year}_'))
        values=json.loads((RAW/income_item['filename']).read_text())
        inc=pd.DataFrame(values[1:],columns=values[0]); inc['unique_id']=inc.state+inc.county
        published=float(inc.set_index('unique_id').loc[row.unique_id,'B19013_001E'])
        cols=[c for c in raw.columns if c.startswith(str(row.year)+'-')]
        assert len(cols)==12
        np.testing.assert_allclose(row.value_to_income,raw.loc[row.unique_id,cols].astype(float).mean()/published)
    assert a.groupby('unique_id').year.apply(set).map(lambda s:s=={2019,2024}).all()
    # Fixed exact-dollar boundary behavior is a reproducibility requirement.
    assert groups.loc[groups.income_2019.eq(43597),'income_group'].eq('Lower').all()
    assert groups.loc[groups.income_2019.eq(50558),'income_group'].eq('Middle').all()
    record={'status':'passed','source_files_checked':len(manifest),'counties':len(eligible),
            'models':len(models),'forecast_rows':len(cv),'county_model_scores':len(saved),
            'checks':['source hashes and credential-free URLs','raw target and naive forecast agreement',
                      'common dates and final-holdout separation','all county metrics independently recomputed',
                      'equal-county group aggregation','affordability ratios recomputed from raw inputs',
                      'exact boundary-tie assignments']}
    (OUT/'verification.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
