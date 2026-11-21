"""Choose geographically spread flat targets from the existing Unity heightmap.

No scan matching or descent outcomes are used in selection.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
raw=ROOT/'LANTERN/Assets/Terrain/site04_height.raw'
meta=json.loads((raw.parent/'site04_height.json').read_text())
spacing=16000/2048
height=np.fromfile(raw,dtype='<u2').reshape(2049,2049).astype(float)
height=height/65535*(meta['max_m']-meta['min_m'])+meta['min_m']
gz,gx=np.gradient(height,spacing)
window=maximum_filter(np.rad2deg(np.arctan(np.hypot(gx,gz))),size=7)
j,i=np.where(window<5)
valid=(i*spacing>=1400)&(i*spacing<=14600)&(j*spacing>=1400)&(j*spacing<=14600)
j,i=j[valid],i[valid]; coordinates=np.c_[i*spacing,j*spacing]
sites=[dict(id='original',x=6198.,z=8512.)]
distance=((coordinates-[6198,8512])**2).sum(axis=1)
for k in range(4):
    index=int(np.argmax(distance)); x,z=coordinates[index]
    sites.append(dict(id=f'area{k+1:02d}',x=float(x),z=float(z)))
    distance=np.minimum(distance,((coordinates-[x,z])**2).sum(axis=1))
for site in sites:
    j,i=round(site['z']/spacing),round(site['x']/spacing)
    site['target_window_max_slope_deg']=round(float(window[j,i]),3)
    site['surrounding_2km_relief_m']=round(float(np.ptp(height[j-128:j+129,i-128:i+129])),2)
manifest=dict(sites=sites,input_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),selection='farthest-first eligible flat targets; see protocol v2')
target=ROOT/'LANTERN/Assets/Experiments/ExpandedSites.json'
target.write_text(json.dumps(manifest,indent=2)+'\n')
out=ROOT/'deliverables/terrain_matching';out.mkdir(exist_ok=True,parents=True)
fig,ax=plt.subplots(figsize=(9,8),layout='constrained')
im=ax.imshow(height,origin='lower',extent=(0,16,0,16),cmap='terrain')
for site in sites:
    x,z=site['x']/1000,site['z']/1000
    ax.add_patch(Rectangle((x-1.2,z-1.2),2.4,2.4,fill=False,edgecolor='black',lw=1.5))
    ax.plot(x,z,'o',color='white',markeredgecolor='black',ms=7)
    ax.annotate(site['id'],(x,z),xytext=(7,7),textcoords='offset points',fontsize=11,
                bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=2))
ax.set(xlabel='Tile east coordinate (km)',ylabel='Tile north coordinate (km)',
       title='Expanded test areas on the generated Site04 lunar terrain\nSquares show 2.4 km crops; targets selected before test outcomes')
fig.colorbar(im,ax=ax,label='Elevation (m, source DEM datum)')
fig.savefig(out/'expanded_test_areas.png',dpi=170)
plt.close(fig)
print(json.dumps(manifest,indent=2))
