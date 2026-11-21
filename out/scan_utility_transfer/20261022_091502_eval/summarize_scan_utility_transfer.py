"""Verify and report frozen-model transfer without training or selecting a policy."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_scan_utility import verify, KEYS


def summarize(folder):
    r, s = verify(folder)
    assert r.stage.eq('eval').all()
    plan = json.loads((folder/'plan.json').read_text())
    assert plan['dataset'] == 'Site01'
    r['speed_violation'] = r.impact_vz.ge(2) | r.impact_vh.ge(1)

    def aggregate(keys):
        return r.groupby(keys, sort=False).agg(
            n=('id','size'), contacts=('touchdown','sum'), successes=('success','sum'),
            mean_miss_m=('target_miss_m','mean'), median_miss_m=('target_miss_m','median'),
            p90_miss_m=('target_miss_m',lambda v: v.quantile(.9)),
            mean_nav_error_m=('horizontal_error_m','mean'),
            speed_violations=('speed_violation','sum'), max_vz=('impact_vz','max'),
            max_vh=('impact_vh','max')).reset_index()

    tables = {'aggregate':aggregate(['arm']), 'by_area':aggregate(['site_id','arm']),
              'by_condition':aggregate(['condition','arm']),
              'by_area_condition':aggregate(['site_id','condition','arm']),
              'by_altitude':aggregate(['altitude','condition','arm'])}
    for name, table in tables.items():
        table.to_csv(folder/(name+'.csv'), index=False)
    paired = r.pivot(index=KEYS, columns='arm', values='target_miss_m')
    paired.to_csv(folder/'paired_distances.csv')
    comparisons = {}
    for control in ['off','geometric','bounded','old_ml']:
        delta = paired[control]-paired.utility
        comparisons[control] = dict(mean_miss_reduction_m=float(delta.mean()),
            improved=int((delta>0).sum()), worsened=int((delta<0).sum()), tied=int((delta==0).sum()))
    pooled = tables['aggregate'].set_index('arm')
    utility, geometric = pooled.loc['utility'], pooled.loc['geometric']
    supported = bool(utility.mean_miss_m < geometric.mean_miss_m
                     and utility.speed_violations < geometric.speed_violations
                     and utility.successes >= geometric.successes)
    result = dict(cases=len(r), paired_configurations=len(paired), areas=r.site_id.nunique(),
                  transfer_criterion_met=supported, comparisons=comparisons,
                  inference_median_ms=float(s.trust_ms.median()), inference_p95_ms=float(s.trust_ms.quantile(.95)))
    (folder/'result_summary.json').write_bytes((json.dumps(result, indent=2)+'\n').encode())
    lines = ['# Frozen scan-utility model: Site01 transfer results', '',
             f'{len(r)} descents; {len(paired)} paired configurations; {r.site_id.nunique()} terrain areas.', '',
             'No training or policy tuning on these outcomes. The policy is the previously selected v2 hybrid.', '',
             '| Policy | Successful landings | Mean miss | Speed violations |', '|---|---:|---:|---:|']
    for row in tables['aggregate'].itertuples():
        lines.append(f'| {row.arm} | {row.successes}/{row.n} | {row.mean_miss_m:.2f} m | {row.speed_violations} |')
    lines += ['', 'Prewritten transfer criterion met: **'+str(supported)+'**.', '',
              'Criterion: lower pooled mean miss and fewer speed violations without fewer target successes than geometric matching.', '',
              '| Area | Policy | Successes | Mean miss | Speed violations |', '|---|---|---:|---:|---:|']
    for row in tables['by_area'].itertuples():
        lines.append(f'| {row.site_id} | {row.arm} | {row.successes}/{row.n} | {row.mean_miss_m:.2f} m | {row.speed_violations} |')
    lines += ['', '| Condition | Policy | Successes | Mean miss | Speed violations |','|---|---|---:|---:|---:|']
    for row in tables['by_condition'].itertuples():
        lines.append(f'| {row.condition} | {row.arm} | {row.successes}/{row.n} | {row.mean_miss_m:.2f} m | {row.speed_violations} |')
    lines += ['', '## Interpretation limits', '',
              'Site01 is separate from the scan-utility training and selection terrain. It appeared in older separate sensor studies, so it is not globally unseen project data.',
              'Three crops share one DEM and simulator. No mission-level statistical significance follows. Actual contact and both impact-speed limits matter; all model failures are retained.',
              'Read environment.txt for the Unity version. Comparisons within this batch use identical software; comparisons with historical Site04 results may also reflect editor-version changes.',
              'No results from this batch may be relabelled as an untouched test after subsequent tuning.', '',
              'Raw trajectories, sparse clouds, scan decisions, model/policy snapshots, terrain, protocol and hash records are preserved.', '']
    (folder/'REPORT.md').write_bytes('\n'.join(lines).encode())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    arms=['off','geometric','bounded','old_ml','utility']
    labels=['OFF','Geometric','Bounded','Old ML','Utility ML']
    colors=['#9ca3af','#087f8c','#d69b30','#b86b6b','#674ab2']
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    for ax,column,title,ylabel in zip(axes,['mean_miss_m','successes','speed_violations'],
            ['Distance from landing target','Successful target landings','Contact-speed violations'],
            ['Mean distance (m)','Count / 162 cases per policy','Count / 162 cases per policy']):
        values=pooled.loc[arms,column].to_numpy()
        bars=ax.bar(labels,values,color=colors,width=.7)
        ax.bar_label(bars,labels=[f'{v:.2f}' if column=='mean_miss_m' else str(int(v)) for v in values],padding=4)
        ax.set_title(title);ax.set_ylabel(ylabel);ax.set_ylim(0,max(values.max()*1.25,1))
        ax.tick_params(axis='x',rotation=25);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('LANTERN: frozen-model transfer to Site01\n810 descents across three separate terrain areas; no retraining',fontsize=16)
    fig.savefig(folder/'results.png',dpi=150);plt.close(fig)
    for file in [Path(__file__), ROOT/'tools/verify_scan_utility.py']:
        shutil.copyfile(file, folder/file.name)
    index = {str(file.relative_to(folder)):hashlib.sha256(file.read_bytes()).hexdigest()
             for file in folder.rglob('*') if file.is_file() and file.name!='ARTIFACT_SHA256.json'}
    (folder/'ARTIFACT_SHA256.json').write_bytes((json.dumps(index,indent=2)+'\n').encode())
    print(tables['aggregate'].to_string(index=False))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    summarize(Path(sys.argv[1]))
