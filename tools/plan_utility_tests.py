"""Freeze diverse development draws and future evaluation terrain before fitting."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter

ROOT=Path(__file__).resolve().parents[1]
dest=ROOT/'LANTERN/Assets/Experiments/ScanUtility';dest.mkdir(parents=True,exist_ok=True)
if (dest/'plan.json').exists(): raise FileExistsError('Utility plan already frozen')
old=json.loads((ROOT/'LANTERN/Assets/Experiments/ExpandedSites.json').read_text())['sites']
prior=json.loads((ROOT/'LANTERN/Assets/Experiments/ScanTrust/FreshSites.json').read_text())['sites']
raw=ROOT/'LANTERN/Assets/Terrain/site04_height.raw'
meta=json.loads((raw.parent/'site04_height.json').read_text())
h=np.fromfile(raw,dtype='<u2').reshape(2049,2049).astype(float)
h=h/65535*(meta['max_m']-meta['min_m'])+meta['min_m']
spacing=16000/2048;gz,gx=np.gradient(h,spacing)
slope=maximum_filter(np.rad2deg(np.arctan(np.hypot(gx,gz))),size=7)
j,i=np.where(slope<5);coords=np.c_[i*spacing,j*spacing]
coords=coords[(coords.min(axis=1)>=1400)&(coords.max(axis=1)<=14600)]
centres=[(s['x'],s['z']) for s in old+prior];fresh=[]
for k in range(3):
    delta=np.abs(coords[:,None,:]-np.array(centres)[None,:,:])
    eligible=(delta.max(axis=2)>=2400).all(axis=1)
    distance=(delta**2).sum(axis=2).min(axis=1);distance[~eligible]=-1
    idx=int(np.argmax(distance))
    if distance[idx]<0:break
    x,z=coords[idx];centres.append((x,z))
    fresh.append(dict(id=f'utility_fresh{k+1:02d}',x=float(x),z=float(z),
                      target_window_max_slope_deg=float(slope[round(z/spacing),round(x/spacing)])))
assert fresh,'No untouched crop available'
rng=np.random.default_rng(314159);collection=[]
for site in old:
    for condition in ['aligned','relief_positive','relief_negative','map_shift']:
        for variant in [0,1]:
            for altitude in [300,600,1200,2000]:
                for k in range(24):
                    angle=rng.uniform(0,2*np.pi);mag=rng.uniform(0,2) if k%8==0 else rng.uniform(5,140)
                    collection.append(dict(site_id=site['id'],condition=condition,variant=variant,
                        altitude=altitude,seed=int(rng.integers(1000,2_000_000)),error_id=f'draw{k:02d}',
                        error_x=float(mag*np.cos(angle)),error_z=float(mag*np.sin(angle)),
                        true_x=float(rng.uniform(-180,180)),true_z=float(rng.uniform(-180,180))))
rng=np.random.default_rng(271828)
development=[]
for k in range(4):
    angle=rng.uniform(0,2*np.pi);mag=rng.uniform(20,110)
    development.append(dict(x=float(mag*np.cos(angle)),z=float(mag*np.sin(angle))))
evaluation=[dict(x=float(m*np.cos(np.deg2rad(a))),z=float(m*np.sin(np.deg2rad(a))))
            for a,m in zip([23,157,281],[35,70,95])]
plan=dict(training_sites=old[:3],validation_sites=old[3:],evaluation_sites=fresh,
          excluded_prior_sites=old+prior,collection=collection,development_errors=development,
          evaluation_errors=evaluation,raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
          protocol_sha256=hashlib.sha256((ROOT/'docs/SCAN_TRUST_PROTOCOL_V2.md').read_bytes()).hexdigest(),
          expected_collect_cases=len(collection),expected_collect_scans=2*len(collection),
          expected_development_cases=672,expected_evaluation_cases=len(fresh)*270)
(dest/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:v for k,v in plan.items() if k not in ['collection','excluded_prior_sites']},indent=2))
