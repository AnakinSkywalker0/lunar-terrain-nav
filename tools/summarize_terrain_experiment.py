"""Summarize saved Unity measurements; no simulation and no training."""
import csv
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path((ROOT/'out/terrain_matching/latest.txt').read_text().strip())
def read(name):
    with (folder/name).open(newline='') as f: return list(csv.DictReader(f))
rows=read('summary.csv'); scans=read('scans.csv')
desc=[r for r in rows if r['kind']=='descent']
station=[r for r in rows if r['kind']=='stationary']
conditions=['aligned','relief_change','map_shift']
f=lambda r,k: float(r[k])
mean=lambda rs,k: float(np.mean([f(r,k) for r in rs])) if rs else float('nan')
stats=[]
for condition in conditions:
    for enabled in ['False','True']:
        group=[r for r in desc if r['condition']==condition and r['matching']==enabled]
        if not group: continue
        stats.append(dict(condition=condition,matching=enabled,n=len(group),touchdowns=sum(r['touchdown']=='True' for r in group),
            successes=sum(r['success']=='True' for r in group),mean_miss_m=mean(group,'target_miss_m'),
            mean_final_error_m=mean(group,'horizontal_error_m'),mean_vertical_error_m=mean(group,'vertical_error_m'),
            max_impact_vz=max(f(r,'impact_vz') for r in group),max_impact_vh=max(f(r,'impact_vh') for r in group),
            accepted_matches=sum(int(r['accepted_matches']) for r in group),wrong_matches=sum(int(r['wrong_matches']) for r in group)))
for r in desc:
    other=[p for p in desc if p['condition']==r['condition'] and p['altitude']==r['altitude'] and p['seed']==r['seed'] and p['matching']!=r['matching']]
    assert len(other)==1, f'Missing paired run for {r["id"]}'
assert len({r['id'] for r in rows})==len(rows), 'Duplicate run IDs'
if folder.name.endswith('_v1'): assert len(desc)==54 and len(station)==27, 'Incomplete v1 matrix'
(folder/'aggregate.json').write_text(json.dumps(stats,indent=2))

plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig, axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
colors=['#167a74','#c48820','#b84444']
for c,color in zip(conditions,colors):
    data=[r for r in station if r['condition']==c]
    if data:
        for altitude in [500,1000,2000]:
            part=[r for r in data if int(r['altitude'])==altitude]
            if part: axes[0,0].scatter([altitude]*len(part),[f(r,'horizontal_error_m') for r in part],color=color,alpha=.7,label=c if altitude==500 else None)
axes[0,0].axhline(np.hypot(60,40),color='#555',linestyle='--',label='Initial error (72.1 m)')
axes[0,0].set(title='Stationary scan: error after accepted correction',xlabel='Starting altitude (m)',ylabel='Horizontal position error (m)')
axes[0,0].legend(fontsize=9)
for idx,c in enumerate(conditions):
    for enabled,offset,color in [('False',-.17,'#d78b42'),('True',.17,'#247f88')]:
        data=[r for r in desc if r['condition']==c and r['matching']==enabled]
        if data:
            values=[f(r,'target_miss_m') for r in data]
            axes[0,1].bar(idx+offset,np.mean(values),.30,color=color,label=('Matching OFF' if enabled=='False' else 'Matching ON') if idx==0 else None)
            axes[0,1].scatter([idx+offset]*len(values),values,color='#222',s=10,alpha=.5)
axes[0,1].set_xticks(range(3),['Aligned','Changed relief','Shifted map'])
axes[0,1].set(title='Actual touchdown distance from target',ylabel='Target miss (m)')
axes[0,1].axhline(10,color='#888',linestyle='--'); axes[0,1].legend(fontsize=9)
for c,ax in [('aligned',axes[1,0]),('map_shift',axes[1,1])]:
    for mode,color in [('off','#d78b42'),('on','#247f88')]:
        path=f'descent_{c}_500_11_{mode}.csv'
        if not (folder/path).exists(): continue
        data=read(path)
        err=[np.hypot(f(r,'ex')-f(r,'x'),f(r,'ez')-f(r,'z')) for r in data]
        ax.plot([f(r,'t') for r in data],err,color=color,label=f'Matching {mode.upper()}')
    ax.set(title=f'500 m example: {c.replace("_"," ")}',xlabel='Simulated time (s)',ylabel='Horizontal position error (m)'); ax.legend(fontsize=9)
fig.suptitle('LANTERN — short-descent terrain matching\nExploratory Site04 simulation • 3-DOF physics • three noise seeds',fontsize=16)
fig.savefig(folder/'results.png',dpi=170); fig.savefig(folder/'results.pdf'); plt.close(fig)

lines=['# Short-descent terrain matching — measured results','',f'Run folder: `{folder.name}`','',
       f'{len(station)} stationary scans and {len(desc)} descents. Paired-run completeness and unique IDs checked.',
       '', '| Map condition | Matching | Runs | Touchdowns | Task successes | Mean target miss | Mean final horizontal error | Wrong / accepted matches |',
       '|---|---|---:|---:|---:|---:|---:|---:|']
for s in stats:
    lines.append(f'| {s["condition"]} | {"ON" if s["matching"]=="True" else "OFF"} | {s["n"]} | {s["touchdowns"]} | {s["successes"]} | {s["mean_miss_m"]:.2f} m | {s["mean_final_error_m"]:.2f} m | {s["wrong_matches"]} / {s["accepted_matches"]} |')
times=[f(r,'match_ms') for r in scans]
lines += ['',f'Matcher latency on this desktop: median {np.median(times):.2f} ms; p95 {np.percentile(times,95):.2f} ms. Excludes scan generation; not a flight-computer benchmark.',
          '', '## How to interpret this', '',
          'Task success means touchdown below 2 m/s vertical speed and 1 m/s horizontal speed, within 10 m of the target. A touchdown can occur without task success.',
          'Wrong match means an accepted proposed correction leaves more than 10 m of horizontal position error. OFF runs compute matches for measurement but do not apply them.',
          'Map-shift tests assess absolute position: a plausible shape match can be confidently wrong when the map coordinate frame is wrong.',
          '', '## Limits', '',
          'This is an exploratory test at one Site04 location, with three noise seeds, fixed initial errors and simplified 3-DOF control. Seeds are not independent terrain sites. No publication/generalisation claim is supported.',
          'The IMU and altimeter are assumed models; attitude response is ideal. The onboard map and simulated ground derive from the same DEM, with controlled perturbations and independent grids. No new physical surface detail is recovered merely by rendering a mesh.',
          'The rendered scene is explicitly a replay of recorded Unity PhysX data. The actual experiments ran in an isolated Unity physics scene, not in Python. Python only summarized and plotted the CSVs. No ML training was performed.',
          '', '## Reproduce', '',
          'In Unity use `SensorTrust/Experiments/Run short-descent protocol v1`, then run `python tools/summarize_terrain_experiment.py`. The output includes the protocol, source snapshots/hashes, map grids, scans and trajectories.',
          '', '![Results](results.png)', '']
(folder/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(stats,indent=2))
print('Saved',folder/'REPORT.md')
