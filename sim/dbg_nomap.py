import sys
sys.path.insert(0,'sim')
import numpy as np, world, engine
w = world.procedural(11, 2.0, 270.0); tr = world.track_for(w)
sc = engine.Scenario('missing', burst_rate=1/60., map_mode='missing'); d = engine.Draws(w, sc, 60, 5)
for j in ['fixed','pitfal','trust2']:
    r = engine.simulate(w, tr, sc, j, d)
    bad = np.nonzero(~r['success'])[0]
    print(j, 'succ', r['success'].mean(), {o:int((r['outcome']==o).sum()) for o in ('landed','crash','rough','timeout')}, 'altRMS', np.sqrt(np.mean(r['alt_sq']/np.maximum(r['alt_n'],1))).round(1))
    if len(bad): print('  failures median vz %.1f vh %.1f slope %.1f miss %.0f fuel %.0f t %.0f' % tuple(np.median(r[k][bad]) for k in ['impact_vz','impact_vh','impact_slope','miss_m','fuel_left','t_end']))
print('--- trace one trust2 run, last 30 steps')
r = engine.simulate(w, tr, sc, 'trust2', d, record_idx=3)
rec = r['rec']
import pandas as pd
df = pd.DataFrame(rec)
print(df[['t','agl_true','agl_est','acc','r','z','ez']].tail(30).round(1).to_string(index=False))
