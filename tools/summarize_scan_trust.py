"""Validate the frozen four-arm Unity experiment and report failures too."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ARMS=['off','geometric','rule','ml']
CONDITIONS=['aligned','relief_change','map_shift']
KEYS=['site_id','condition','altitude','error_id','seed']


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder,smoke=False):
    assert (folder/'status.txt').read_text().startswith('Complete;'),'Incomplete Unity run'
    runs=pd.read_csv(folder/'summary.csv'); scans=pd.read_csv(folder/'scans.csv')
    scans=scans.merge(runs[['id','condition','site_id','altitude','error_id','seed']],on='id',validate='many_to_one')
    assert len(runs)==(12 if smoke else 648) and runs.id.is_unique
    assert set(runs.arm)==set(ARMS)
    assert runs.groupby(KEYS).arm.apply(lambda a:set(a)==set(ARMS)).all()
    first=scans[scans.time_s.eq(0)].set_index('id')
    shared=['points','dx','dz','rms_m','confidence','before_error_m','proposed_error_m','bad_score']
    for _,group in runs.groupby(KEYS):
        initial=first.loc[group.id]
        assert np.allclose(initial[shared].to_numpy(float),initial[shared].iloc[0].to_numpy(float),atol=1e-6,rtol=0)
        assert initial.valid.nunique()==1 and initial.accepted.nunique()==1
    for _,run in runs.iterrows():
        assert (folder/(run.id+'.csv')).exists() and (folder/(run.id+'_cloud.csv')).exists()
        assert run.contact_definition=='PhysX_contact'
        assert bool(run.success)==bool(run.touchdown and run.impact_vz<2 and run.impact_vh<1 and run.target_miss_m<10)
    record=(folder/'source_sha256.txt').read_text().upper()
    for name in ['ScanTrustExperiment.cs','TerrainNavigationCore.cs','PortableScanTrust.cs','ScanTrustVerification.cs',
                 'TerrainTouchdownRecorder.cs','FreshSites.json','model.json','rule.json']:
        assert digest(folder/name).upper() in record,name
    original=ROOT/'out/terrain_matching/20261021_183805_expanded_v2/TerrainNavigationCore.cs'
    assert digest(folder/'TerrainNavigationCore.cs')==digest(original),'Matcher/navigation/guidance changed'
    model=json.loads((folder/'model.json').read_text()); rule=json.loads((folder/'rule.json').read_text())
    trained=ROOT/'out/scan_trust/20261022_model_v1'
    assert digest(folder/'model.json')==digest(trained/'model.json'),'Model changed after freezing'
    assert digest(folder/'rule.json')==digest(trained/'rule.json'),'Rule changed after freezing'
    assert digest(folder/'protocol.md')==digest(trained/'protocol.md'),'Protocol changed after training'
    assert json.loads((folder/'parity_report.json').read_text())['passed']
    assert np.isfinite(scans.bad_score).all() and scans.bad_score.between(0,1).all()
    expected_ml=scans.valid & scans.accepted & scans.bad_score.lt(model['bad_score_threshold'])
    expected_rule=scans.valid & scans.accepted & scans.rms_m.le(rule['max_rms_m']) & scans.confidence.ge(rule['min_confidence'])
    assert np.array_equal(expected_ml,scans.ml_accept),'ML veto routing differs'
    assert np.array_equal(expected_rule,scans.rule_accept),'Rule routing differs'
    expected_apply=(scans.arm.eq('geometric')&scans.accepted)|(scans.arm.eq('rule')&expected_rule)|(scans.arm.eq('ml')&expected_ml)
    assert np.array_equal(expected_apply,scans.applied),'Controller correction routing differs'
    assert np.array_equal(scans.applied&scans.proposed_error_m.gt(10),scans.applied_bad)
    (folder/'VERIFICATION.md').write_text(
        f'{len(runs)} unique completed cases; four complete arms per configuration; identical initial sensor/matcher/model inputs across arms; '
        'all trajectory/cloud files present; success criteria recomputed; source and model/rule/protocol hashes verified; '
        'frozen geometric core unchanged; Python/Unity parity passed; ML and rule decision routing recomputed from logged diagnostics.\n')
    return runs,scans


def summarize(folder):
    runs,scans=verify(folder)
    def aggregate(keys):
        return runs.groupby(keys,sort=False).agg(n=('id','size'),contacts=('touchdown','sum'),successes=('success','sum'),
            mean_miss_m=('target_miss_m','mean'),median_miss_m=('target_miss_m','median'),
            p90_miss_m=('target_miss_m',lambda x:np.percentile(x,90)),
            mean_nav_error_m=('horizontal_error_m','mean'),max_vz=('impact_vz','max'),max_vh=('impact_vh','max'),
            mean_fuel_kg=('fuel_kg','mean')).reset_index()
    grouped=aggregate(['condition','arm']); by_site=aggregate(['site_id','condition','arm'])
    grouped.to_csv(folder/'aggregate.csv',index=False); by_site.to_csv(folder/'by_site.csv',index=False)
    aggregate(['altitude','condition','arm']).to_csv(folder/'by_altitude.csv',index=False)
    aggregate(['error_id','condition','arm']).to_csv(folder/'by_error.csv',index=False)
    gate=scans.groupby(['condition','arm'],sort=False).agg(scans=('id','size'),
        geometric_accepted=('accepted','sum'),applied=('applied','sum'),applied_bad=('applied_bad','sum'),
        median_inference_ms=('trust_ms','median'),p95_inference_ms=('trust_ms',lambda s:s.quantile(.95))).reset_index()
    gate.to_csv(folder/'gate_audit.csv',index=False)
    paired=runs.pivot(index=KEYS,columns='arm',values='target_miss_m')
    for control in ('off','geometric','rule'): paired['ml_reduction_vs_'+control]=paired[control]-paired.ml
    paired.to_csv(folder/'paired_differences.csv')
    # Conditional intervals resample paired configurations, not correlated scan rows.
    rng=np.random.default_rng(8841); comparisons={}
    for control in ('off','geometric','rule'):
        delta=(paired[control]-paired.ml).to_numpy()
        boot=delta[rng.integers(0,len(delta),size=(5000,len(delta)))].mean(axis=1)
        comparisons[control]=dict(mean_miss_reduction_m=float(delta.mean()),
            improved=int((delta>0).sum()),worsened=int((delta<0).sum()),tied=int((delta==0).sum()),
            conditional_95_interval_m=np.quantile(boot,[.025,.975]).tolist(),
            caveat='Paired configuration bootstrap conditional on these three areas; not cross-site generalization uncertainty')
    summary=dict(cases=len(runs),configurations=len(paired),comparisons=comparisons,
                 model_sha256=digest(folder/'model.json'),status=(folder/'status.txt').read_text(),
                 inference_median_ms=float(scans.trust_ms.median()),inference_p95_ms=float(scans.trust_ms.quantile(.95)))
    (folder/'result_summary.json').write_text(json.dumps(summary,indent=2)+'\n')

    colors=['#a6a6a6','#27868d','#d69a3a','#7056a5']
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
    for j,arm in enumerate(ARMS):
        values=[grouped.query('condition==@c and arm==@arm').iloc[0] for c in CONDITIONS]
        axes[0,0].bar(np.arange(3)+(j-1.5)*.19,[v.successes/54*100 for v in values],width=.18,color=colors[j],label=arm)
        axes[0,1].bar(np.arange(3)+(j-1.5)*.19,[v.mean_miss_m for v in values],width=.18,color=colors[j])
    for ax in axes[0]: ax.set_xticks(range(3),['Accurate map','Changed terrain','Shifted map'])
    axes[0,0].set(title='Target success (54 descents per bar)',ylabel='Success (%)',ylim=(0,110))
    axes[0,0].legend(ncol=2);axes[0,1].set(title='Final distance from target',ylabel='Mean distance (m)')
    for j,arm in enumerate(ARMS):
        g=gate[gate.arm.eq(arm)].set_index('condition')
        axes[1,0].bar(np.arange(3)+(j-1.5)*.19,[g.loc[c,'applied_bad'] for c in CONDITIONS],width=.18,color=colors[j])
    axes[1,0].set_xticks(range(3),['Accurate','Changed','Shifted'])
    axes[1,0].set(title='Wrong corrections actually applied',ylabel='Count across evolving trajectories')
    for c,color in zip(CONDITIONS,['#27868d','#d69a3a','#b44f4f']):
        group=paired.reset_index().query('condition==@c')
        axes[1,1].scatter(group.geometric,group.ml,s=25,alpha=.65,color=color,label=c)
    lim=max(paired.geometric.max(),paired.ml.max())*1.05
    axes[1,1].plot([0,lim],[0,lim],'--',color='#888')
    axes[1,1].set(xlabel='Geometric target miss (m)',ylabel='ML target miss (m)',title='Same configuration; below line favours ML')
    axes[1,1].legend(fontsize=9)
    fig.suptitle('LANTERN learned scan trust: fresh closed-loop evaluation\n648 Unity descents • three new Site04 areas • frozen model and thresholds',fontsize=16)
    fig.savefig(folder/'results.png',dpi=160);fig.savefig(folder/'results.pdf');plt.close(fig)

    totals=runs.groupby('arm').agg(n=('id','size'),successes=('success','sum'),mean_miss_m=('target_miss_m','mean'))
    ml_success=int(totals.loc['ml','successes']);geo_success=int(totals.loc['geometric','successes'])
    lines=['# Learned scan trust: measured closed-loop results','',
           '648 descents in three fresh, nonoverlapping Site04 areas; 162 paired four-arm configurations.',
           'Initial offsets, noise seeds, relief perturbation and map translation differ from training.',
           f'The learned policy achieved {ml_success}/162 target successes; geometric matching achieved {geo_success}/162. '
           'This experiment does not support replacing the geometric gate with the learned veto.',
           '', '| Map | Arm | Successes / 54 | Contacts | Mean target miss | Median | Max sideways impact |',
           '|---|---|---:|---:|---:|---:|---:|']
    for c in CONDITIONS:
        for arm in ARMS:
            r=grouped.query('condition==@c and arm==@arm').iloc[0]
            lines.append(f'| {c} | {arm} | {r.successes}/54 | {r.contacts} | {r.mean_miss_m:.2f} m | {r.median_miss_m:.2f} m | {r.max_vh:.2f} m/s |')
    lines+=['','## Paired ML comparisons','']
    for control,r in comparisons.items():
        lo,hi=r['conditional_95_interval_m']
        lines.append(f"ML versus {control}: mean target-distance reduction {r['mean_miss_reduction_m']:.2f} m; "
                     f"{r['improved']} improved / {r['worsened']} worsened / {r['tied']} tied of162. "
                     f"Conditional paired-bootstrap interval [{lo:.2f}, {hi:.2f}] m.")
    lines+=['','These intervals resample paired configurations within the three observed areas. '
             'They do not establish performance at independent lunar sites. All areas share Site04.',
             '',f"Median inference {summary['inference_median_ms']:.4f} ms; p95 {summary['inference_p95_ms']:.4f} ms on this desktop, including both rule and ML evaluations, excluding scan matching.",
             '', '## Interpretation limits','',
             'The classifier sees only local matcher diagnostics. It has no independent absolute position reference. '
             'A globally translated map remains intrinsically ambiguous from shape fit alone. Rejecting more corrections '
             'can reduce wrong updates while leaving the initial navigation error uncorrected.',
             'The raw summary accepted_matches/wrong_matches count geometric proposals. '
             'Use scan applied/applied_bad fields and gate_audit.csv for updates actually used by a policy.',
             'The selected forest and threshold were chosen on area03 validation before these runs and were not changed after smoke or full outcomes. '
             'The original geometric core, controller, altimeter model and older experiment outputs are preserved.',
             'The new integration controls correction use in the isolated estimated-state Unity experiment. '
             'It does not retrofit the original 102.5km Site04 scene. Vehicle attitude is idealized; sensors are synthetic.',
             '', '## Reproduction','',
             'Protocol: SCAN_TRUST_PROTOCOL_V1.md. Unity menu: SensorTrust/Experiments/Run scan-trust protocol v1. '
             'Summarize with python tools/summarize_scan_trust.py. Frozen source, model/rule, protocol, parity report, '
             'case trajectories/clouds, scan decisions and source hashes are saved beside this report.',
             '', '![Measured results](results.png)','']
    (folder/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    print(grouped.to_string(index=False));print(json.dumps(comparisons,indent=2))


if __name__=='__main__':
    folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path((ROOT/'out/scan_trust/latest_closed_loop.txt').read_text().strip())
    if '--smoke' in sys.argv:
        verify(folder,True);print('Smoke verification passed:',folder)
    else: summarize(folder)
