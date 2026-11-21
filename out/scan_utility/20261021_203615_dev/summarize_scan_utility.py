"""Select v2 policy on development missions, then report a separate final test."""
import json
import hashlib
from pathlib import Path
import shutil
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.verify_scan_utility import verify,KEYS

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def summarize(folder):
    r,s=verify(folder);stage=r.stage.iloc[0]
    assert stage in ('dev','eval'),'Summarize full development or final stages only'
    r['speed_violation']=r.impact_vz.ge(2)|r.impact_vh.ge(1)
    def aggregate(keys):
        return r.groupby(keys,sort=False).agg(n=('id','size'),contacts=('touchdown','sum'),successes=('success','sum'),
            mean_miss_m=('target_miss_m','mean'),median_miss_m=('target_miss_m','median'),p90_miss_m=('target_miss_m',lambda x:x.quantile(.9)),
            mean_nav_error_m=('horizontal_error_m','mean'),speed_violations=('speed_violation','sum'),max_vz=('impact_vz','max'),max_vh=('impact_vh','max'),
            mean_fuel_kg=('fuel_kg','mean')).reset_index()
    pooled=aggregate(['arm']);grouped=aggregate(['condition','arm'])
    pooled.to_csv(folder/'aggregate.csv',index=False);grouped.to_csv(folder/'by_condition.csv',index=False)
    aggregate(['altitude','condition','arm']).to_csv(folder/'by_altitude.csv',index=False)
    aggregate(['error_id','condition','arm']).to_csv(folder/'by_error.csv',index=False)
    s=s.merge(r[['id','condition','site_id']],on='id',validate='many_to_one')
    audit=s.groupby(['condition','arm'],sort=False).agg(scans=('id','size'),applied=('applied','sum'),
        absolute_bad_applied=('applied_bad','sum'),beneficial_applied=('beneficial_applied','sum'),
        mean_applied_gain=('applied_gain','mean'),inference_p50_ms=('trust_ms','median'),inference_p95_ms=('trust_ms',lambda x:x.quantile(.95))).reset_index()
    audit.to_csv(folder/'correction_audit.csv',index=False)
    paired=r.pivot(index=KEYS,columns='arm',values='target_miss_m');paired.to_csv(folder/'paired_distances.csv')
    if stage=='dev':
        order=['utility_hard','utility_soft','utility_hybrid']
        candidates=pooled[pooled.arm.isin(order)].copy();candidates['order']=candidates.arm.map({k:i for i,k in enumerate(order)})
        chosen=candidates.sort_values(['successes','speed_violations','mean_miss_m','order'],ascending=[False,True,True,True]).iloc[0].arm
        choice=dict(policy=chosen,selection_source=str(folder.resolve()),source_sha256=sha(folder/'summary.csv'),
            model_sha256=sha(folder/'utility_model.json'),protocol_sha256=sha(folder/'protocol.md'),
            criterion='max target success, min speed violations, min mean miss, fixed policy order',
            final_evaluation_used=False)
        output=ROOT/'LANTERN/Assets/Experiments/ScanUtility/policy.json'
        if output.exists():raise FileExistsError('Policy already frozen')
        output.write_text(json.dumps(choice,indent=2)+'\n')
        (folder/'selected_policy.json').write_text(json.dumps(choice,indent=2)+'\n')
    else:
        chosen=json.loads((folder/'policy.json').read_text())['policy']
        assets=ROOT/'LANTERN/Assets/Experiments/ScanUtility'
        assert sha(folder/'policy.json')==sha(assets/'policy.json')
    comparison={}
    evaluated='utility' if stage=='eval' else chosen
    for control in ['off','geometric','bounded','old_ml']:
        delta=paired[control]-paired[evaluated]
        comparison[control]=dict(mean_miss_reduction_m=float(delta.mean()),improved=int((delta>0).sum()),
                                 worsened=int((delta<0).sum()),tied=int((delta==0).sum()))
    result=dict(stage=stage,selected_policy=chosen,cases=len(r),paired_configurations=len(paired),comparisons=comparison,
                evaluation_areas=int(r.site_id.nunique()),model_sha256=sha(folder/'utility_model.json'),
                speed_definition='>=2m/s vertical or >=1m/s horizontal; target success also requires contact and miss<10m')
    (folder/'result_summary.json').write_text(json.dumps(result,indent=2)+'\n')

    arms=pooled.arm.tolist();conditions=['aligned','relief_positive','map_shift']
    colors=['#969696','#27868d','#d79d3b','#bb6666','#7056a5','#719e61','#4f71a5'][:len(arms)]
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
    width=.8/len(arms)
    for i,arm in enumerate(arms):
        g=grouped[grouped.arm.eq(arm)].set_index('condition')
        axes[0,0].bar(np.arange(3)+(i-(len(arms)-1)/2)*width,[100*g.loc[c,'successes']/g.loc[c,'n'] for c in conditions],width=width*.95,label=arm,color=colors[i])
        axes[0,1].bar(np.arange(3)+(i-(len(arms)-1)/2)*width,[g.loc[c,'mean_miss_m'] for c in conditions],width=width*.95,color=colors[i])
    for ax in axes[0]:ax.set_xticks(range(3),['Accurate map','Changed terrain','Shifted map'])
    axes[0,0].set(title='Target success',ylabel='Success (%)',ylim=(0,110));axes[0,0].legend(fontsize=9,ncol=2)
    axes[0,1].set(title='Final distance from target',ylabel='Mean miss (m)')
    if stage=='eval':
        for c,color in zip(conditions,['#27868d','#d79d3b','#bb6666']):
            g=paired.reset_index().query('condition==@c');axes[1,0].scatter(g.geometric,g.utility,color=color,label=c,s=30,alpha=.7)
        limit=max(paired.geometric.max(),paired.utility.max())*1.05;axes[1,0].plot([0,limit],[0,limit],'--',color='#888')
        axes[1,0].set(xlabel='Geometric target miss (m)',ylabel='Utility ML target miss (m)',title='Paired configurations; below line favours utility')
        axes[1,0].legend(fontsize=9)
    else:
        axes[1,0].bar(arms,pooled.speed_violations,color=colors);axes[1,0].tick_params(axis='x',rotation=30)
        axes[1,0].set(title='Development contact-speed violations',ylabel='Descents')
    axes[1,1].bar(arms,pooled.mean_nav_error_m,color=colors);axes[1,1].tick_params(axis='x',rotation=30)
    axes[1,1].set(title='Final navigation error',ylabel='Mean horizontal error (m)')
    fig.suptitle(f'LANTERN utility trust v2: {stage} • {len(r)} descents\nSelected policy: {chosen} • {r.site_id.nunique()} terrain area(s) within Site04',fontsize=16)
    fig.savefig(folder/'results.png',dpi=160);fig.savefig(folder/'results.pdf');plt.close(fig)

    lines=[f'# Scan utility v2: {stage} results','',f'{len(r)} descents; {len(paired)} paired configurations. Selected policy: {chosen}.','',
        '| Arm | Successes | Contacts | Mean target miss | Speed violations |','|---|---:|---:|---:|---:|']
    for row in pooled.itertuples():lines.append(f'| {row.arm} | {row.successes}/{row.n} | {row.contacts} | {row.mean_miss_m:.2f}m | {row.speed_violations} |')
    lines+=['','| Condition | Arm | Successes | Mean miss |','|---|---|---:|---:|']
    for row in grouped.itertuples():lines.append(f'| {row.condition} | {row.arm} | {row.successes}/{row.n} | {row.mean_miss_m:.2f}m |')
    lines+=['','This utility model rewards useful error reduction, rather than rejecting every correction that leaves >10m error. '
            'Partial corrections and small updates require the original geometric gate. Ground truth supplies labels/evaluation only.',
            'Development outcomes selected the policy. Final evaluation uses a separately reserved area, new offsets, seeds, perturbations and1500m altitude. '
            'Only one nonoverlapping fresh eligible crop remained; this is a narrow Site04 test, not independent-site generalization evidence.',
            'A coherent global map shift still needs independent registration information. Local match diagnostics cannot uniquely establish absolute location.',
            'All records, routing checks, frozen source/model/protocol, trajectories and sparse clouds are retained. '
            'Compare methods within this batch: actual start offsets and map perturbations differ from v1.',
            '', '![Results](results.png)','']
    (folder/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    print(pooled.to_string(index=False));print('Selected policy:',chosen);print(json.dumps(comparison,indent=2))

if __name__=='__main__':summarize(Path(sys.argv[1]))
