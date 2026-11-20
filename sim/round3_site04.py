"""Round-3 evaluation on the held-out real site Site04. RUN ONCE, after docs/PREREG_ROUND3.md is frozen and tagged.

  python sim/round3_site04.py --allow-site04        output: out/round3/site04.csv

Refuses to run unless ALL of these hold:
  * --allow-site04 is given;
  * git tag `prereg-round3` exists and HEAD is exactly that commit (frozen code);
  * sim/engine.py, sim/round3_site04.py, sim/round3_candidates.py and docs/PREREG_ROUND3.md have no uncommitted changes;
  * out/round3/site04.csv does not exist yet (the pre-registration forbids re-runs after seeing results).
Settings are the frozen ones in docs/PREREG_ROUND3.md: n = 500 per cell, seed 20261201, confidence-gated camera for every judge,
time stamps for every judge in the delayed condition. The verdicts for Q1-Q5 are computed by `evaluate` below from the output.
"""
import argparse
import dataclasses
import multiprocessing as mp
import os
import pickle
import subprocess
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round3")
TAG = "prereg-round3"
FROZEN_FILES = ["sim/engine.py", "sim/round3_site04.py", "sim/round3_candidates.py", "docs/PREREG_ROUND3.md"]
N, SEED = 500, 20261201
CL = "cliff + faults (nominal noise)"
X4, X8, X16 = "x4 below 6000 m", "x8 below 6000 m (TRAINING)", "x16 below 6000 m"
SHADOW_NOISY = "x8 below 6000 m (TRAINING)"
LABEL_BOTH = (CL, X8)       # these cells are scored with the old and the noise-aware label; the others with the noise-aware label


def run_git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def check_frozen(git=run_git, csv_exists=None):
    """Return an error string if the run is not allowed, else None. `git` is injectable for tests."""
    tag = git("rev-parse", "-q", "--verify", "refs/tags/" + TAG + "^{commit}")
    if tag.returncode != 0:
        return "git tag %s does not exist: freeze docs/PREREG_ROUND3.md (commit and tag) first" % TAG
    head = git("rev-parse", "HEAD")
    if head.stdout.strip() != tag.stdout.strip():
        return "HEAD is not the commit tagged %s: run from the frozen commit" % TAG
    dirty = git("diff", "--quiet", "HEAD", "--", *FROZEN_FILES)
    if dirty.returncode != 0:
        return "frozen files have uncommitted changes: " + ", ".join(FROZEN_FILES)
    exists = os.path.exists(os.path.join(OUT, "site04.csv")) if csv_exists is None else csv_exists
    if exists:
        return "out/round3/site04.csv already exists: the pre-registration forbids re-running Site04 after seeing results"
    return None


def verdicts(df):
    """Pre-registered decision rules Q1-Q5 (docs/PREREG_ROUND3.md). df has columns condition, config, label, success_pct, missed_fault_pct."""
    s = df[df.label == "aware"].groupby(["condition", "config"]).success_pct.mean().unstack()
    d = lambda a, b, c: float(s.loc[c, a] - s.loc[c, b])          # noqa: E731
    F, T, PT, W, M, P2 = "tolerance + noise floor", "tolerance", "pitfal", "trust2", "wait", "pitfal"
    out = {}
    out["Q1"] = (all(d(F, T, c) >= 10 for c in (X4, X8, X16)), {c: round(d(F, T, c), 1) for c in (X4, X8, X16)})
    out["Q2"] = (all(d(F, PT, c) >= 0 for c in (X8, X16)) and d(F, PT, CL) >= -3,
                 {c: round(d(F, PT, c), 1) for c in (X8, X16, CL)})
    out["Q3"] = (d(F, W, CL) >= -3 and d(F, W, X8) >= 0, {c: round(d(F, W, c), 1) for c in (CL, X8)})
    q4 = {}
    for j in ("wait", "ml"):
        if j + " + terrain_R" in s.columns and j in s.columns:
            q4[j] = {c: round(d(j + " + terrain_R", j, c), 1) for c in (CL, X8)}
    out["Q4"] = (bool(q4) and all(v >= 5 for r in q4.values() for v in r.values()), q4)
    m = df[(df.label == "aware") & (df.condition == SHADOW_NOISY) & (df.config == "trust2")].missed_fault_pct.mean()
    out["Q5"] = (bool(m < 10), {"trust2 missed-fault % (noise-aware label), shadow + noisy x8": round(float(m), 1)})
    return out


def task(spec):
    cond, label, scen = spec
    import engine
    import pipeline as P
    from round3_candidates import CONFIGS, ML_PATH
    w, tr = P.get_world(("site04", P.SUN_EL, P.SUN_AZ))
    mdl = pickle.load(open(ML_PATH, "rb")) if os.path.exists(ML_PATH) else None
    rows = []
    for name, (judge, extra) in CONFIGS.items():
        if judge == "ml" and mdl is None:
            continue
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw.update(extra)
        kw["fault_label_noise_aware"] = label == "aware"
        if cond.startswith("delayed"):
            kw["timestamps"] = True
        r = engine.simulate(w, tr, scen, judge, engine.Draws(w, scen, N, SEED), ml_model=mdl if judge == "ml" else None, **kw)
        s = engine.summarize(r)
        rows.append(dict(condition=cond, config=name, label=label, n=N, success_pct=s["success_pct"], ci_lo=s["success_lo"],
                         ci_hi=s["success_hi"], alt_rms_m=s["alt_rms_m"], false_rej_pct=s["false_rej_pct"],
                         missed_fault_pct=s["missed_fault_pct"]))
    print(time.strftime("%H:%M:%S"), cond, label, flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-site04", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if not a.allow_site04:
        sys.exit("Refusing to run: Site04 is the held-out test site. Freeze docs/PREREG_ROUND3.md, tag it, then pass --allow-site04.")
    err = check_frozen()
    if err:
        sys.exit("Refusing to run: " + err)
    import engine
    from ml2_noise_normal import CONDS
    conds = dict(CONDS)
    conds["delayed altimeter (time-stamped for every judge)"] = engine.SCENARIOS["delayed"]
    conds["altimeter dropout (exploratory)"] = engine.SCENARIOS["dropout"]
    specs = [(c, lab, sc) for c, sc in conds.items() for lab in (("aware", "old") if c in LABEL_BOTH else ("aware",))]
    os.makedirs(OUT, exist_ok=True)
    with mp.Pool(min(a.workers, 6)) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "site04.csv"), index=False)
    t = df[df.label == "aware"].groupby(["condition", "config"]).success_pct.mean().unstack().round(1)
    print("\nSite04 landing success % (500 runs per cell)\n", t.to_string())
    print("\nPre-registered verdicts")
    for q, (ok, vals) in verdicts(df).items():
        print(q, "MET" if ok else "NOT met", vals)


if __name__ == "__main__":
    mp.freeze_support()
    main()
