"""Round-4 held-out evaluation on RESERVED procedural worlds 17-20. RUN ONCE, after docs/PREREG_ROUND4.md is frozen and tagged.

  python sim/round4_heldout.py --allow-heldout        output: out/round4/heldout.csv

Refuses to run unless ALL of these hold:
  * --allow-heldout is given;
  * git tag `prereg-round4` exists and HEAD is exactly that commit (frozen code);
  * the frozen files have no uncommitted changes;
  * out/round4/heldout.csv does not exist yet (no re-runs after seeing results).
Settings are the frozen ones in docs/PREREG_ROUND4.md: worlds procedural 17-20, seed 20261215, n = 200 per cell, confidence-gated camera,
noise-aware fault label, 3 beams (assumed geometry) with independent AND common-mode beam faults, single-beam rule R4 with a 100 m map offset.
Site04 is never used. Simulation only.
"""
import argparse
import dataclasses
import multiprocessing as mp
import os
import subprocess
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round4")
TAG = "prereg-round4"
FROZEN_FILES = ["sim/engine.py", "sim/round4_heldout.py", "sim/round4_dev.py", "docs/PREREG_ROUND4.md"]
SEEDS, SEED, N = (17, 18, 19, 20), 20261215, 200
CONDS = ("cliff", "x4", "x8", "x16")
PB, CA, CB = "pitfal_mb", "A: floor (both) + footprint terrain", "B: floor (update only) + footprint terrain"
REFS = ("tolerance_mb", "tol_mb + floor (both)", "tol_mb + oracle noise (not deployable)")
ST, SF = "single tolerance", "single tolerance + floor (both)"


def run_git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def check_frozen(git=run_git, csv_exists=None):
    """Return an error string if the run is not allowed, else None. `git` is injectable for tests."""
    tag = git("rev-parse", "-q", "--verify", "refs/tags/" + TAG + "^{commit}")
    if tag.returncode != 0:
        return "git tag %s does not exist: freeze docs/PREREG_ROUND4.md (commit and tag) first" % TAG
    head = git("rev-parse", "HEAD")
    if head.stdout.strip() != tag.stdout.strip():
        return "HEAD is not the commit tagged %s: run from the frozen commit" % TAG
    if git("diff", "--quiet", "HEAD", "--", *FROZEN_FILES).returncode != 0:
        return "frozen files have uncommitted changes: " + ", ".join(FROZEN_FILES)
    exists = os.path.exists(os.path.join(OUT, "heldout.csv")) if csv_exists is None else csv_exists
    if exists:
        return "out/round4/heldout.csv already exists: the pre-registration forbids re-running after seeing results"
    return None


def verdicts(df):
    """Pre-registered rules R1-R4 (docs/PREREG_ROUND4.md). df: columns part, fault_mode, condition, config, success_pct (one row per world)."""
    m = df[df.part == "multi"].groupby(["fault_mode", "condition", "config"]).success_pct.mean()
    d = lambda mode, c, a, b: float(m[(mode, c, a)] - m[(mode, c, b)])          # noqa: E731
    modes = ("independent", "common")
    out = {}
    out["R1"] = (all(d(md, c, CB, PB) >= -3 for md in modes for c in ("cliff", "x4", "x8")),
                 {"%s %s" % (md, c): round(d(md, c, CB, PB), 1) for md in modes for c in ("cliff", "x4", "x8")})
    out["R2"] = (all(d(md, "x16", CB, PB) >= 3 for md in modes), {md: round(d(md, "x16", CB, PB), 1) for md in modes})
    out["R3"] = (all(d(md, c, CA, PB) >= -3 for md in modes for c in ("cliff", "x4")),
                 {"%s %s" % (md, c): round(d(md, c, CA, PB), 1) for md in modes for c in ("cliff", "x4")})
    s = df[df.part == "single"].groupby("config").success_pct.mean()
    out["R4"] = (bool(s[SF] - s[ST] >= -3), {"floor minus plain tolerance, 100 m map offset": round(float(s[SF] - s[ST]), 1)})
    return out


def task(spec):
    import engine
    import pipeline as P
    import round4_dev as D
    part, seed_w, cond, mode = spec
    w, tr = P.get_world(("proc", seed_w))
    if part == "multi":
        scen = D.NOISE[cond]
        cfgs = {PB: D.MULTI["pitfal_mb"], CA: D.MULTI["tol_mb + floor (both) + footprint terrain"],
                CB: D.MULTI["tol_mb + floor (variance only) + footprint terrain"], REFS[0]: D.MULTI["tolerance_mb"],
                REFS[1]: D.MULTI["tol_mb + floor (both)"], REFS[2]: D.MULTI["tol_mb + oracle noise (not deployable)"]}
    else:
        scen = D.SINGLE_CONDS["wrong100"]
        cfgs = {ST: D.SINGLE["tolerance"], SF: D.SINGLE["tolerance + floor (both)"]}
    rows = []
    for name, (judge, extra) in cfgs.items():
        kw = dict(P.tuned())
        kw["cam_policy"] = "conf"
        kw["fault_label_noise_aware"] = True
        kw.update(extra)
        if part == "multi":
            kw.update(beams=3, beam_fault=mode)
        r = engine.simulate(w, tr, scen, judge, engine.Draws(w, scen, N, SEED), **kw)
        s = engine.summarize(r)
        rows.append(dict(part=part, world=str(("proc", seed_w)), condition=cond, fault_mode=mode, config=name, n=N,
                         success_pct=s["success_pct"], ci_lo=s["success_lo"], ci_hi=s["success_hi"], alt_rms_m=s["alt_rms_m"],
                         false_rej_pct=s["false_rej_pct"], missed_fault_pct=s["missed_fault_pct"]))
    print(time.strftime("%H:%M:%S"), part, seed_w, cond, mode, flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-heldout", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if not a.allow_heldout:
        sys.exit("Refusing to run: worlds 17-20 are reserved. Freeze docs/PREREG_ROUND4.md, tag it, then pass --allow-heldout.")
    err = check_frozen()
    if err:
        sys.exit("Refusing to run: " + err)
    specs = [("multi", s, c, m) for s in SEEDS for c in CONDS for m in ("independent", "common")] + [("single", s, "wrong100", "single") for s in SEEDS]
    os.makedirs(OUT, exist_ok=True)
    with mp.Pool(min(a.workers, 6)) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "heldout.csv"), index=False)
    print(df[df.part == "multi"].groupby(["fault_mode", "condition", "config"]).success_pct.mean().unstack(0).round(1).to_string())
    print(df[df.part == "single"].groupby("config").success_pct.mean().round(1).to_string())
    print("\nPre-registered verdicts")
    for q, (ok, vals) in verdicts(df).items():
        print(q, "MET" if ok else "NOT met", vals)


if __name__ == "__main__":
    mp.freeze_support()
    main()
