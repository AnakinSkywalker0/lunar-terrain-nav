"""Freeze new, nonoverlapping terrain crops before training or new outcomes."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter

ROOT=Path(__file__).resolve().parents[1]
raw=ROOT/'LANTERN/Assets/Terrain/site04_height.raw'
meta=json.loads((raw.parent/'site04_height.json').read_text())
height=np.fromfile(raw,dtype='<u2').reshape(2049,2049).astype(float)
height=height/65535*(meta['max_m']-meta['min_m'])+meta['min_m']
spacing=16000/2048
gz,gx=np.gradient(height,spacing)
slope=maximum_filter(np.rad2deg(np.arctan(np.hypot(gx,gz))),size=7)
j,i=np.where(slope<5)
coords=np.c_[i*spacing,j*spacing]
valid=(coords.min(axis=1)>=1400)&(coords.max(axis=1)<=14600)
coords=coords[valid]
old=json.loads((ROOT/'LANTERN/Assets/Experiments/ExpandedSites.json').read_text())['sites']
centres=[(s['x'],s['z']) for s in old]
sites=[]
for k in range(3):
    difference=np.abs(coords[:,None,:]-np.array(centres)[None,:,:])
    eligible=(difference.max(axis=2)>=2400).all(axis=1)
    distance=(difference**2).sum(axis=2).min(axis=1)
    distance[~eligible]=-1
    index=int(np.argmax(distance))
    assert distance[index]>0,'No nonoverlapping eligible crop remains'
    x,z=coords[index]; centres.append((x,z))
    sites.append(dict(id=f'fresh{k+1:02d}',x=float(x),z=float(z),
                      target_window_max_slope_deg=float(slope[round(z/spacing),round(x/spacing)])))
manifest=dict(sites=sites,old_centres=old,selection='farthest-first, flat, edge-safe, no 2.4km crop overlap',
              input_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
dest=ROOT/'LANTERN/Assets/Experiments/ScanTrust';dest.mkdir(exist_ok=True,parents=True)
path=dest/'FreshSites.json'
if path.exists(): raise FileExistsError('Fresh sites already frozen')
path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
