"""Experiment pipeline (parallel). Usage: python sim/pipeline.py <stage> [...]

Stages: ml | tune | main | sweeps | replay | all
Everything is seeded; results go to out/mc/. Jobs run in a process pool, one world cached per worker.
"""
import json
import multiprocessing as mp
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import world as W  # noqa: E402

OUT = os.path.join(W.ROOT, "out", "mc")
os.makedirs(OUT, exist_ok=True)
N_MAIN = 500
SUN_EL, SUN_AZ = 2.0, 270.0
TRAIN_SEEDS = [21, 22, 23, 24, 25, 26]
TUNE_SEEDS = [11, 12, 13]
MAIN_JUDGES = ["fixed", "pitfal", "tolerance", "wait", "second", "ml", "trust", "trust_scan"]
ABLATIONS = ["trust_nocam", "trust_noprob", "trust_nophys"]
WORKERS = 6

_worlds = {}
_ml = [None, False]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def get_world(key):
    if key not in _worlds:
        _worlds.clear()
        if key[0] == "site04":
            w = W.site04_world(0, key[1], key[2])
        elif key[0] == "site01":
            w = W.site01_world(0, key[1], key[2])
        else:
            w = W.procedural(key[1], SUN_EL, SUN_AZ)
        _worlds[key] = (w, W.track_for(w))
    return _worlds[key]


def get_ml():
    if not _ml[1]:
        p = os.path.join(OUT, "ml_model.pkl")
        if os.path.exists(p):
            with open(p, "rb") as f:
                _ml[0] = pickle.load(f)
        _ml[1] = True
    return _ml[0]


def tuned():
    p = os.path.join(OUT, "tuned.json")
    return json.load(open(p)) if os.path.exists(p) else dict(K_prob=10, sigma_probation=3.0)


def warm(keys):
    """Build worlds sequentially once so shadow caches exist before the pool starts."""
    for k in keys:
        log("warm", k)
        get_world(k)


def run_job(job):
    """job: dict(world, scen, judge, n, seed, kw, tag, per_run, collect)"""
    w, tr = get_world(job["world"])
    sc = job["scen"]
    d = engine.Draws(w, sc, job["n"], job["seed"])
    kw = dict(tuned())
    kw.update(job.get("kw") or {})
    t0 = time.time()
    col = [] if job.get("collect") else None
    r = engine.simulate(w, tr, sc, job["judge"], d, scan=job["judge"].endswith("_scan"), ml_model=get_ml(), collect=col, **kw)
    s = engine.summarize(r)
    s.update(judge=job["judge"], scenario=sc.name, tag=job.get("tag", ""), secs=time.time() - t0)
    if job.get("per_run"):
        os.makedirs(job["per_run"], exist_ok=True)
        fn = f"{job.get('tag','')}{sc.name.split()[0]}_{job['judge']}.csv".replace("/", "_")
        pd.DataFrame({k: r[k] for k in ["success", "outcome", "impact_vz", "impact_vh", "impact_slope", "fuel_left", "miss_m", "t_end"]}).to_csv(
            os.path.join(job["per_run"], fn), index_label="run")
    if col is not None:
        s["_collect"] = col
    return s


def pmap(jobs, workers=WORKERS):
    out = []
    with mp.Pool(min(workers, len(jobs))) as pool:
        for s in pool.imap_unordered(run_job, jobs):
            if "_collect" not in s:
                log(f"  {s['scenario'][:34]:34s} {s['judge']:12s} {s['tag']:>14s} success {s['success_pct']:5.1f}% [{s['success_lo']:.0f},{s['success_hi']:.0f}] altRMS {s['alt_rms_m']:7.1f} frej {s['false_rej_pct']:5.1f} miss {s['missed_fault_pct']:5.1f} ({s['secs']:.0f}s)")
            out.append(s)
    return out


# ------------------------------------------------------------------ ML
def stage_ml():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score
    warm([("proc", s) for s in TRAIN_SEEDS])
    jobs = []
    for s in TRAIN_SEEDS:
        for name in ["cliff", "cliff_fault", "shadow_noisy", "delayed"]:
            jobs.append(dict(world=("proc", s), scen=engine.SCENARIOS[name], judge="pitfal", n=100, seed=1000 + s, collect=True, tag=f"w{s}"))
    res = pmap(jobs)
    Xs, ys, gs = [], [], []
    for r in res:
        seed = int(r["tag"][1:])
        for X, y in r["_collect"]:
            Xs.append(X); ys.append(y); gs.append(np.full(len(y), seed))
    X = np.concatenate(Xs); y = np.concatenate(ys).astype(int); g = np.concatenate(gs)
    held = g == TRAIN_SEEDS[-1]
    rf = RandomForestClassifier(n_estimators=120, max_depth=14, min_samples_leaf=20, n_jobs=-1, random_state=0, class_weight="balanced")
    rf.fit(X[~held], y[~held])
    p = rf.predict_proba(X[held])[:, 1]
    rep = dict(n_train=int((~held).sum()), n_heldout=int(held.sum()), fault_frac=float(y.mean()),
               heldout_accuracy=float(((p > 0.5) == y[held]).mean()), heldout_auc=float(roc_auc_score(y[held], p)))
    log("ML report", rep)
    rf.fit(X, y)   # final model: all training worlds (Site04 never used)
    with open(os.path.join(OUT, "ml_model.pkl"), "wb") as f:
        pickle.dump(rf, f)
    json.dump(rep, open(os.path.join(OUT, "ml_report.json"), "w"), indent=2)


# ------------------------------------------------------------------ tuning on procedural worlds + Site01 only
def stage_tune():
    site01 = ("site01", SUN_EL, SUN_AZ)
    warm([("proc", s) for s in TUNE_SEEDS] + [site01])
    worlds = [("proc", s) for s in TUNE_SEEDS] + [site01]
    jobs = []
    for K in (8, 10, 12):
        for sp in (2.5, 3.0, 4.0):
            for wk in worlds:
                for name in ["cliff_fault", "shadow_noisy", "delayed"]:
                    jobs.append(dict(world=wk, scen=engine.SCENARIOS[name], judge="trust2", n=100, seed=7,
                                     kw=dict(K_prob=K, sigma_probation=sp, cam_policy="conf"), tag=f"K{K}_s{sp}"))
    res = pmap(jobs)
    df = pd.DataFrame(res)
    df["K_prob"] = df.tag.str.extract(r"K(\d+)").astype(int)
    df["sigma_probation"] = df.tag.str.extract(r"_s([\d.]+)").astype(float)
    g = df.groupby(["K_prob", "sigma_probation"]).agg(success=("success_pct", "mean"), false_rej=("false_rej_pct", "mean"), missed=("missed_fault_pct", "mean")).reset_index()
    g.to_csv(os.path.join(OUT, "tuning.csv"), index=False)
    best = g.sort_values(["success", "false_rej"], ascending=[False, True]).iloc[0]
    json.dump(dict(K_prob=int(best.K_prob), sigma_probation=float(best.sigma_probation)), open(os.path.join(OUT, "tuned.json"), "w"))
    log("tuning table\n" + g.to_string())
    log("chosen", dict(best))


def tuned():
    p = os.path.join(OUT, "tuned.json")
    return json.load(open(p)) if os.path.exists(p) else dict(K_prob=10, sigma_probation=3.0)


# ------------------------------------------------------------------ main Monte Carlo on Site04 (run once, after the freeze)
MAIN_JUDGES = ["fixed", "pitfal", "tolerance", "wait", "second", "ml", "trust", "trust2", "trust2_scan"]
ABL = ["trust_nophys", "trust_noprob"]


def stage_main():
    key = ("site04", SUN_EL, SUN_AZ)
    warm([key])
    w, tr = get_world(key)
    json.dump(dict(track=tr, tuned=tuned(), n=N_MAIN, sun_el=SUN_EL, sun_az=SUN_AZ, camera="conf (matcher confidence gate) for every judge"),
              open(os.path.join(OUT, "main_config.json"), "w"), default=float, indent=2)
    pr = os.path.join(OUT, "per_run")
    jobs = []
    for sk in ["cliff", "cliff_fault", "shadow_noisy", "delayed", "dropout"]:
        for j in MAIN_JUDGES + ABL:
            jobs.append(dict(world=key, scen=engine.SCENARIOS[sk], judge=j, n=N_MAIN, seed=20260101, per_run=pr, kw=dict(cam_policy="conf")))
    res = pmap(jobs)
    pd.DataFrame(res).to_csv(os.path.join(OUT, "main_results.csv"), index=False)


def stage_policies():
    """Camera policy comparison for one filter family: naive / matcher confidence / Sun-geometry prediction / both."""
    key = ("site04", SUN_EL, SUN_AZ)
    warm([key])
    jobs = []
    for sk in ["cliff", "shadow_noisy"]:
        for j in ("pitfal", "trust2"):
            for pol in ("naive", "conf", "aware", "both"):
                jobs.append(dict(world=key, scen=engine.SCENARIOS[sk], judge=j, n=N_MAIN, seed=20260101, kw=dict(cam_policy=pol), tag=pol))
    res = pmap(jobs)
    pd.DataFrame(res).to_csv(os.path.join(OUT, "camera_policies.csv"), index=False)


# ------------------------------------------------------------------ sweeps and robustness
def stage_sweeps():
    key = ("site04", SUN_EL, SUN_AZ)
    site01 = ("site01", SUN_EL, SUN_AZ)
    suns = [("site04", el, az) for el in (1.5, 2.0, 3.0) for az in (90.0, 180.0, 270.0)]
    warm([key, site01] + suns)
    kw = dict(cam_policy="conf")
    jobs = []
    for sig in (5, 20, 50, 100, 200, 400):
        sc = engine.Scenario("cliff", burst_rate=1 / 150.0, init_pos_sigma=float(sig))
        for j in ("pitfal", "trust2"):
            jobs.append(dict(world=key, scen=sc, judge=j, n=300, seed=31, tag=f"sig{sig}", kw=kw))
    for mode, label in [("wrong", "map shifted 2 km"), ("missing", "no map")]:
        sc = engine.Scenario(label, burst_rate=1 / 60.0, map_mode=mode)
        for j in ("fixed", "pitfal", "trust2"):
            jobs.append(dict(world=key, scen=sc, judge=j, n=300, seed=41, tag=f"map_{mode}", kw=kw))
    sc = engine.Scenario("mid-descent divert", burst_rate=1 / 60.0, divert=True)
    for j in ("fixed", "pitfal", "trust2"):
        jobs.append(dict(world=key, scen=sc, judge=j, n=300, seed=51, tag="divert", kw=kw))
    for wk, lab in [(site01, "Site01(tuned on)"), (key, "Site04(unseen)")]:
        for sk in ["cliff", "cliff_fault", "shadow_noisy", "delayed"]:
            for j in ("pitfal", "trust2"):
                jobs.append(dict(world=wk, scen=engine.SCENARIOS[sk], judge=j, n=300, seed=61, tag=f"site_{lab}", kw=kw))
    for (_, el, az) in suns:
        for j in ("pitfal", "trust2"):
            jobs.append(dict(world=("site04", el, az), scen=engine.SCENARIOS["shadow_noisy"], judge=j, n=200, seed=71, tag=f"sun_el{el}_az{az:.0f}", kw=kw))
    res = pmap(jobs)
    df = pd.DataFrame(res)
    df.to_csv(os.path.join(OUT, "sweeps_all.csv"), index=False)
    df[df.tag.str.startswith("sig")].assign(value=lambda d: d.tag.str[3:].astype(float)).to_csv(os.path.join(OUT, "sweeps_a.csv"), index=False)
    df[df.tag.str.startswith("sun_")].to_csv(os.path.join(OUT, "sweeps_sun.csv"), index=False)


# ------------------------------------------------------------------ replay export for Unity
def stage_replay():
    key = ("site04", SUN_EL, SUN_AZ)
    w, tr = get_world(key)
    ml = get_ml()
    rd = os.path.join(W.ROOT, "out", "replay")
    os.makedirs(rd, exist_ok=True)
    sc = engine.SCENARIOS["cliff_fault"]
    d = engine.Draws(w, sc, 100, 20260101)
    kw = tuned()
    ra = {j: engine.simulate(w, tr, sc, j, d, ml_model=ml, cam_policy="conf", **kw) for j in ("fixed", "pitfal", "trust2")}
    cand = np.nonzero(ra["trust2"]["success"] & ~ra["fixed"]["success"] & ~ra["pitfal"]["success"])[0]
    if len(cand) == 0:
        cand = np.nonzero(ra["trust2"]["success"] & ~ra["fixed"]["success"])[0]
    idx = int(cand[0]) if len(cand) else 0
    meta = dict(run=idx, track=tr, scenario=sc.name, outcome={j: str(ra[j]["outcome"][idx]) for j in ra})
    for j in ("fixed", "pitfal", "trust2"):
        r = engine.simulate(w, tr, sc, j, d, ml_model=ml, record_idx=idx, cam_policy="conf", **kw)
        pd.DataFrame(r["rec"]).to_csv(os.path.join(rd, f"replay_{j}.csv"), index=False)
    json.dump(meta, open(os.path.join(rd, "replay_meta.json"), "w"), indent=2, default=float)
    log("replay run", idx, meta["outcome"])


if __name__ == "__main__":
    mp.freeze_support()
    stages = sys.argv[1:] or ["all"]
    if "all" in stages:
        stages = ["ml", "tune", "main", "policies", "sweeps", "replay"]
    for s in stages:
        log("=== stage", s)
        globals()["stage_" + s]()
