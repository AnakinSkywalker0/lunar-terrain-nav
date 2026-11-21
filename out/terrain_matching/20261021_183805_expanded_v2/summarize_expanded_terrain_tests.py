"""Validate and summarize the expanded Unity experiment. No training/simulation."""
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path((ROOT/'out/terrain_matching/latest_expanded.txt').read_text().strip())
assert (folder/'status.txt').read_text().startswith('Complete;'), 'Batch is not complete'
data=pd.read_csv(folder/'summary.csv')
scans=pd.read_csv(folder/'scans.csv')
descent=data[data.kind.eq('descent')].copy(); stationary=data[data.kind.eq('stationary')].copy()
assert len(data)==810 and len(descent)==540 and len(stationary)==270, 'Incomplete matrix'
assert data.id.is_unique
keys=['site_id','condition','altitude','error_id','seed']
off=descent[~descent.matching].set_index(keys)
on=descent[descent.matching].set_index(keys)
assert off.index.is_unique and on.index.is_unique and off.index.equals(on.index)
assert len(on)==270
first=scans[scans.time_s.eq(0)&scans.id.str.startswith('descent_')].set_index('id')
shared=['points','dx','dz','rms_m','confidence','before_error_m','proposed_error_m']
for key in on.index:
    before=first.loc[off.loc[key,'id']]; after=first.loc[on.loc[key,'id']]
    assert np.allclose(before[shared].astype(float),after[shared].astype(float),rtol=0,atol=1e-6),f'Initial sensor/match mismatch: {key}'
    assert before.accepted==after.accepted and before.valid==after.valid
for _,r in data.iterrows():
    assert (folder/(r.id+'.csv')).exists() and (folder/(r.id+'_cloud.csv')).exists(), r.id
    if r.kind=='descent':
        expected=bool(r.touchdown and r.impact_vz<2 and r.impact_vh<1 and r.target_miss_m<10)
        assert expected==bool(r.success), r.id
recorded=(folder/'source_sha256.txt').read_text().upper()
for name in ['ShortDescentExperiment.cs','TerrainNavigationCore.cs','TerrainTouchdownRecorder.cs','ExpandedSites.json']:
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest().upper() in recorded,name
v1=ROOT/'out/terrain_matching/20261021_181450_v1/TerrainNavigationCore.cs'
assert hashlib.sha256(v1.read_bytes()).digest()==hashlib.sha256((folder/'TerrainNavigationCore.cs').read_bytes()).digest(), 'Algorithm changed'

paired=on[['target_miss_m','horizontal_error_m','success']].join(off[['target_miss_m','horizontal_error_m','success']],lsuffix='_on',rsuffix='_off')
paired['miss_reduction_m']=paired.target_miss_m_off-paired.target_miss_m_on
paired.to_csv(folder/'paired_differences.csv')
conditions=['aligned','relief_change','map_shift']; sites=['original','area01','area02','area03','area04']
def aggregate(columns):
    return descent.groupby(columns,sort=False).agg(n=('id','size'),touchdowns=('touchdown','sum'),successes=('success','sum'),
        mean_miss_m=('target_miss_m','mean'),median_miss_m=('target_miss_m','median'),p90_miss_m=('target_miss_m',lambda v:np.percentile(v,90)),
        mean_final_error_m=('horizontal_error_m','mean'),max_impact_vz=('impact_vz','max'),max_impact_vh=('impact_vh','max'),
        accepted_matches=('accepted_matches','sum'),wrong_matches=('wrong_matches','sum'),attempted_matches=('attempted_matches','sum')).reset_index()
pooled=aggregate(['condition','matching']); by_site=aggregate(['site_id','condition','matching'])
pooled.to_csv(folder/'aggregate.csv',index=False); by_site.to_csv(folder/'by_site.csv',index=False)
aggregate(['altitude','condition','matching']).to_csv(folder/'by_altitude.csv',index=False)
aggregate(['error_id','condition','matching']).to_csv(folder/'by_initial_error.csv',index=False)
pooled.to_json(folder/'aggregate.json',orient='records',indent=2)

plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
positions=[]; values=[]; colors=[]
for i,c in enumerate(conditions):
    for mode,color,shift in [(False,'#d78b42',-.19),(True,'#247f88',.19)]:
        values.append(descent.loc[descent.condition.eq(c)&descent.matching.eq(mode),'target_miss_m'].to_numpy())
        positions.append(i+shift); colors.append(color)
bp=axes[0,0].boxplot(values,positions=positions,widths=.30,patch_artist=True,showfliers=True)
for patch,color in zip(bp['boxes'],colors): patch.set_facecolor(color)
axes[0,0].set_xticks(range(3),['Accurate map','Changed terrain','Shifted map'])
axes[0,0].set(ylabel='Final distance from target (m)',title='OFF (orange) / ON (teal), 90 descents per group')
axes[0,0].axhline(10,color='#777',linestyle='--',lw=1)
matrix=np.array([[int(on.reset_index().query('site_id == @s and condition == @c').success.sum()) for c in conditions] for s in sites])
axes[0,1].imshow(matrix,vmin=0,vmax=18,cmap='YlGnBu',aspect='auto')
axes[0,1].set_xticks(range(3),['Accurate','Changed','Shifted']); axes[0,1].set_yticks(range(5),sites)
axes[0,1].set(title='Target successes with matching ON (out of 18)')
for i in range(5):
    for j in range(3): axes[0,1].text(j,i,f'{matrix[i,j]}/18',ha='center',va='center',color='white' if matrix[i,j]>10 else 'black')
for c,color in zip(conditions,['#167a74','#c48820','#b84444']):
    for a,shift in [(500,-18),(2000,18)]:
        group=stationary[stationary.condition.eq(c)&stationary.altitude.eq(a)]
        axes[1,0].scatter([a+shift]*len(group),group.horizontal_error_m,s=18,alpha=.45,color=color,label=c if a==500 else None)
axes[1,0].set(xlabel='Altitude (m)',ylabel='Remaining estimate error (m)',title='Stationary scan outcomes, including rejected matches')
axes[1,0].legend(fontsize=9)
for c,color in zip(conditions,['#167a74','#c48820','#b84444']):
    ids=set(descent.loc[descent.condition.eq(c)&descent.matching,'id'])
    group=scans[scans.id.isin(ids)&scans.accepted].copy()
    if len(group)>2500: group=group.iloc[np.linspace(0,len(group)-1,2500,dtype=int)]
    axes[1,1].scatter(group.confidence,np.maximum(group.proposed_error_m,.05),s=5,alpha=.2,color=color,label=c)
axes[1,1].set_yscale('log'); axes[1,1].axhline(10,color='#777',linestyle='--')
axes[1,1].set(xlabel='Heuristic match confidence (not a probability)',ylabel='Absolute error after proposed correction (m)',title='Accepted corrections can still be wrong')
axes[1,1].legend(fontsize=9)
fig.suptitle('LANTERN expanded terrain test — 540 descents, 270 stationary scans\nFive areas in Site04 • fixed matcher • three error patterns × three seeds',fontsize=16)
fig.savefig(folder/'expanded_results.png',dpi=170); fig.savefig(folder/'expanded_results.pdf'); plt.close(fig)

lines=['# Expanded terrain-matching test: measured results','',f'Folder: `{folder.name}`','',
       '270 stationary scans and 540 descents (270 matched OFF/ON pairs). Five regions in the same lunar DEM, two starting altitudes, three initial position errors, three noise seeds, three map conditions.',
       '', '| Map condition | Matching | Runs | Contacts | Target successes | Mean final distance | Median | 90th percentile |',
       '|---|---|---:|---:|---:|---:|---:|---:|']
for c in conditions:
    for mode in [False,True]:
        r=pooled[pooled.condition.eq(c)&pooled.matching.eq(mode)].iloc[0]
        lines.append(f'| {c} | {"ON" if mode else "OFF"} | {r.n} | {r.touchdowns} | {r.successes} | {r.mean_miss_m:.2f} m | {r.median_miss_m:.2f} m | {r.p90_miss_m:.2f} m |')
lines+=['','## Area-level target successes','', '| Area | Accurate OFF / ON | Changed OFF / ON | Shifted OFF / ON |','|---|---:|---:|---:|']
for s in sites:
    cells=[]
    for c in conditions:
        a=by_site[by_site.site_id.eq(s)&by_site.condition.eq(c)&~by_site.matching].iloc[0]
        b=by_site[by_site.site_id.eq(s)&by_site.condition.eq(c)&by_site.matching].iloc[0]
        cells.append(f'{a.successes}/18 / {b.successes}/18')
    lines.append('| '+s+' | '+' | '.join(cells)+' |')
lines+=['','## Pairing and limitations','',
    f'Matching reduced final target distance in {(paired.miss_reduction_m>0).sum()}/270 pairs and increased it in {(paired.miss_reduction_m<0).sum()}/270. Mean paired reduction: {paired.miss_reduction_m.mean():.2f} m. Pooled figures can hide site/condition failures; use the tables above.',
    f'Geometric contact: {int(descent.touchdown.sum())}/540. Contacts below 2 m/s vertical: {int((descent.touchdown & descent.impact_vz.lt(2)).sum())}/540. A slow touchdown can miss the target.',
    f'Matcher desktop latency: median {scans.match_ms.median():.2f} ms, p95 {scans.match_ms.quantile(.95):.2f} ms, excluding scan generation. This is not flight-computer timing.',
    'Target success requires actual PhysX terrain contact, vertical speed <2 m/s, horizontal speed <1 m/s and target miss <10 m. Final distances include timeouts; the Contacts column identifies completion.',
    'V2 records actual collision relative velocity; v1 used an 8 cm proximity stop. Compare the OFF/ON arms within this batch rather than treating differences from v1 as an algorithm improvement.',
    'Matcher, navigation and guidance source hashes match v1 exactly. Terrain setup is cached; vehicle, filter, fuel and random generator reset per run. No ML training or threshold tuning was performed.',
    'The five targets were chosen before outcomes using a deterministic distance/slope rule. All targets are in Site04. This tests variation within one dataset; it does not establish performance at other lunar sites. The vehicle still has ideal attitude response and 3-DOF dynamics.',
    'Confidence is residual contrast, not calibrated probability. A globally shifted map can match shapes well while being wrong in absolute coordinates; diagnosing that requires independent registration evidence.',
    '', '## Evidence and reproduction','',
    'Protocol, site manifest, frozen C# source and SHA-256 hashes, 810 trajectory/cloud pairs, scan records and per-site/per-altitude/per-error tables are saved here.',
    'Unity menu: `SensorTrust/Experiments/Run expanded terrain protocol v2`. Plan: `python tools/plan_expanded_terrain_tests.py`. Summarize completed data: `python tools/summarize_expanded_terrain_tests.py`.',
    '', '![Expanded results](expanded_results.png)','']
(folder/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
(folder/'VERIFICATION.md').write_text('810 unique cases; 270 complete OFF/ON pairs; initial scan and matcher outputs agree within every pair before correction; all trajectory/cloud files present; success labels recomputed; source snapshot hashes verified; algorithm source identical to frozen v1.\n',encoding='utf-8')
print(pooled.to_string(index=False));print('Saved',folder/'REPORT.md')
