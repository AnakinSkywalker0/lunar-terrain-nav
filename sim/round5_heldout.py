"""Round-5 held-out evaluation on RESERVED procedural worlds 41-50. RUN ONCE, after docs/PREREG_ROUND5.md is frozen and tagged.

  python sim/round5_heldout.py --allow-heldout        output: out/round5/heldout.csv

Refuses to run unless ALL of these hold:
  * --allow-heldout is given;
  * git tag `prereg-round5` exists and HEAD is exactly that commit (frozen code);
  * the frozen files have no uncommitted changes;
  * out/round5/heldout.csv does not exist yet (no re-runs after seeing results).
Settings are the frozen ones in docs/PREREG_ROUND5.md: worlds procedural 41-50, seed 20261221, n = 200 per cell, confidence-gated camera,
noise-aware fault label, three beams (assumed geometry) with independent AND common-mode faults, single-beam rules S5-S7.
Site04 and worlds 17-20 are never used. Simulation only.
"""
import argparse
import multiprocessing as mp
import os
import subprocess
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "round5")
TAG = "prereg-round5"
FROZEN_FILES = ["sim/engine.py", "sim/round5_heldout.py", "sim/round5_dev.py", "sim/round5_train.py", "docs/PREREG_ROUND5.md"]
SEEDS, SEED, N = tuple(range(41, 51)), 20261221, 200
CONDS = ("cliff", "x4", "x8", "x16")
PB, A, B, S = "baseline: PITFAL-style multi-beam", "A: floor both + footprint terrain", "B: floor update-only + footprint terrain", "B2 Student-t (4 dof) + floor"
SP, SA, ST, DE, CS = "baseline: PITFAL-style", "A: tolerance + noise floor", "B2 Student-t (4 dof) + floor", "A4 delay estimation (no stamps)", "B4 soft camera weighting + floor"
IMM = "A3 IMM-style noise modes"
SINGLE_CONDS = {"cliff": None, "x8": None, "x16": None, "delayed_nots": None, "wrong100": None, "wrong2000": None}
# (config, conditions it is run in); None = all single-beam conditions
SINGLE_PLAN = {SP: None, SA: None, ST: None, IMM: None, DE: ["delayed_nots"], CS: ["cliff", "x8"]}


def run_git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def check_frozen(git=run_git, csv_exists=None):
    """Return an error string if the run is not allowed, else None. `git` is injectable for tests."""
    tag = git("rev-parse", "-q", "--verify", "refs/tags/" + TAG + "^{commit}")
    if tag.returncode != 0:
        return "git tag %s does not exist: freeze docs/PREREG_ROUND5.md (commit and tag) first" % TAG
    head = git("rev-parse", "HEAD")
    if head.stdout.strip() != tag.stdout.strip():
        return "HEAD is not the commit tagged %s: run from the frozen commit" % TAG
    if git("diff", "--quiet", "HEAD", "--", *FROZEN_FILES).returncode != 0:
        return "frozen files have uncommitted changes: " + ", ".join(FROZEN_FILES)
    exists = os.path.exists(os.path.join(OUT, "heldout.csv")) if csv_exists is None else csv_exists
    if exists:
        return "out/round5/heldout.csv already exists: the pre-registration forbids re-running after seeing results"
    return None


def verdicts(df):
    """Pre-registered rules S1-S7 (docs/PREREG_ROUND5.md). df: columns part, fault_mode, condition, config, world, success_pct (one row per world)."""
    m = df[df.part == "multi"].groupby(["fault_mode", "condition", "config"]).success_pct.mean()
    d = lambda mode, c, a, b: float(m[(mode, c, a)] - m[(mode, c, b)])          # noqa: E731
    modes = ("independent", "common")
    out = {}
    low = ("cliff", "x4", "x8")
    out["S1"] = (all(d(md, c, S, PB) >= -3 for md in modes for c in low), {"%s %s" % (md, c): round(d(md, c, S, PB), 1) for md in modes for c in low})
    out["S2"] = (all(d(md, "x16", S, PB) >= 3 for md in modes), {md: round(d(md, "x16", S, PB), 1) for md in modes})
    out["S3"] = (all(d(md, c, S, A) >= 3 for md in modes for c in low), {"%s %s" % (md, c): round(d(md, c, S, A), 1) for md in modes for c in low})
    pw = df[(df.part == "multi") & (df.fault_mode == "independent") & (df.config == S) & df.condition.isin(["cliff", "x4"])]
    worst = float(pw.success_pct.min())
    out["S4"] = (worst >= 50.0, {"lowest world score (cliff, x4)": round(worst, 1)})
    s = df[df.part == "single"].groupby(["condition", "config"]).success_pct.mean()
    out["S5"] = (bool(s[("delayed_nots", DE)] - s[("delayed_nots", SA)] >= 20), {"delayed, no stamps: De minus A1s": round(float(s[("delayed_nots", DE)] - s[("delayed_nots", SA)]), 1)})
    out["S6"] = (all(s[(c, CS)] - s[(c, SA)] >= 3 for c in ("cliff", "x8")), {c: round(float(s[(c, CS)] - s[(c, SA)]), 1) for c in ("cliff", "x8")})
    out["S7"] = (bool(s[("x16", ST)] - s[("x16", SA)] >= 3), {"x16: St minus A1s": round(float(s[("x16", ST)] - s[("x16", SA)]), 1)})
    return out


def task(spec):
    import pipeline as P
    import round5_dev as D
    part, seed_w, cond, mode = spec
    wk = ("proc", seed_w)
    if part == "multi":
        cfgs = {k: D.MULTI[k] for k in (PB, A, B, S)}
        scen = D.MULTI_CONDS[cond]
    else:
        cfgs = {k: (D.SINGLE[k][0], D.SINGLE[k][1], conds) for k, conds in SINGLE_PLAN.items()}
        scen = D.SINGLE_CONDS[cond]
    rows = D.one(part, wk, SEED, cond, scen, cfgs, N, mode if part == "multi" else None)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-heldout", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if not a.allow_heldout:
        sys.exit("Refusing to run: worlds 41-50 are reserved. Freeze docs/PREREG_ROUND5.md, tag it, then pass --allow-heldout.")
    err = check_frozen()
    if err:
        sys.exit("Refusing to run: " + err)
    specs = [("multi", s, c, m) for s in SEEDS for c in CONDS for m in ("independent", "common")] + [("single", s, c, None) for s in SEEDS for c in SINGLE_CONDS]
    os.makedirs(OUT, exist_ok=True)
    with mp.Pool(min(a.workers, 6)) as pool:
        rows = [r for part in pool.imap_unordered(task, specs) for r in part]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "heldout.csv"), index=False)
    pd.set_option("display.width", 250)
    print(df[df.part == "multi"].groupby(["fault_mode", "condition", "config"]).success_pct.mean().unstack(0).round(1).to_string())
    print(df[df.part == "single"].groupby(["condition", "config"]).success_pct.mean().unstack(0).round(1).to_string())
    print("\nPre-registered verdicts")
    for q, (ok, vals) in verdicts(df).items():
        print(q, "MET" if ok else "NOT met", vals)


if __name__ == "__main__":
    mp.freeze_support()
    main()
