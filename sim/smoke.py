import sys, time
sys.path.insert(0, 'sim')
import numpy as np, world, engine
w = world.site04_world(sun_az=270.0); tr = world.track_for(w)
n = 100
for name in ['cliff', 'shadow_noisy', 'delayed']:
    sc = engine.SCENARIOS[name]; d = engine.Draws(w, sc, n, 5)
    for j in ['pitfal', 'trust', 'trust2']:
        t0 = time.time(); r = engine.simulate(w, tr, sc, j, d); s = engine.summarize(r)
        print(f"{name:13s} {j:7s} succ {s['success_pct']:5.1f}%  frej {s['false_rej_pct']:5.1f} miss {s['missed_fault_pct']:5.1f}  ({time.time()-t0:.0f}s)")
sc = engine.Scenario('missing', burst_rate=1/60., map_mode='missing'); d = engine.Draws(w, sc, n, 5)
for j in ['pitfal', 'trust', 'trust2']:
    r = engine.simulate(w, tr, sc, j, d); s = engine.summarize(r); print(f"no-map        {j:7s} succ {s['success_pct']:5.1f}%")
