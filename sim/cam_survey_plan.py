"""Plan camera-survey sample positions on Site04: stratified by lit fraction of the camera footprint."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world as W

w = W.site04_world(0, 2.0, 270.0)
rng = np.random.default_rng(2026)
cand = 6000
x = rng.uniform(1800, 14200, cand)
y = rng.uniform(1800, 14200, cand)
agl = rng.uniform(1500, 5000, cand)
rf = np.clip(agl * 0.36, 60, 3840)
lit = w.true_lit.litfrac(x, y, rf)
rough = w.true_lit.hstd(x, y, rf)
bins = [0, 0.05, 0.25, 0.5, 0.8, 1.01]
sel = []
for lo, hi in zip(bins[:-1], bins[1:]):
    idx = np.nonzero((lit >= lo) & (lit < hi))[0]
    take = rng.choice(idx, size=min(60, len(idx)), replace=False)
    sel += list(take)
    print(f"lit {lo:.2f}-{hi:.2f}: {len(idx)} candidates, took {len(take)}")
ground = w.truth.height(x[sel], y[sel])
out = []
for k, i in enumerate(sel):
    out.append(dict(id=k, x=float(x[i]), z=float(16000.0 - y[i]), y_sim=float(y[i]), agl=float(agl[i]), ground=float(ground[k]),
                    lit=float(lit[i]), rough=float(rough[i]),
                    dx=float(rng.uniform(-100, 100)), dz=float(rng.uniform(-100, 100)),
                    dsun_el=float(rng.uniform(0.05, 0.25)), dsun_az=float(rng.uniform(-1.0, 1.0))))
json.dump(dict(items=out), open("out/camera_survey/positions.json", "w"))
print(len(out), "samples")
