import sys, time
sys.path.insert(0, 'sim')
import numpy as np, world, engine
t0 = time.time()
w = world.site04_world(sun_az=270.0)
tr = world.track_for(w)
print('world', time.time() - t0)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
scen_name = sys.argv[2] if len(sys.argv) > 2 else 'cliff'
sc = engine.SCENARIOS[scen_name]
d = engine.Draws(w, sc, n, 1)
for j in sys.argv[3:] or ['fixed', 'pitfal', 'trust']:
    t1 = time.time()
    r = engine.simulate(w, tr, sc, j, d)
    s = engine.summarize(r)
    print(f"{j:10s} {time.time()-t1:5.1f}s succ {s['success_pct']:5.1f}%  outcomes L{s['outcome_landed']} C{s['outcome_crash']} R{s['outcome_rough']} T{s['outcome_timeout']}  altRMS {s['alt_rms_m']:8.1f}  frej {s['false_rej_pct']:5.1f}  miss {s['missed_fault_pct']:5.1f}  fuel {s['fuel_left_kg']:6.1f} camw {s['cam_weight_in_shadow']:.2f}")
