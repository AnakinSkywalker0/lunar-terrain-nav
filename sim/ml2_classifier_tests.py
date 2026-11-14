"""Is the fault classifier really needed? Two follow-ups to sim/ml2_ablate.py.

Experiment 3  classifier ablation on FRESH worlds: accept ALL flagged readings / reject ALL flagged readings, same worlds and seeds
              as sim/ml2_fresh.py (procedural 14-16 seed 101; tuning worlds seed 202), compared with the full non-ML-noise control
              and with PITFAL / trust v2 from out/ml2/fresh.csv.
Experiment 4  a NON-ML replacement for the classifier: `ml2_rule_gate`, a tolerance-style chi-square gate whose noise level adapts
              (running innovation estimate s_hat), with the same terrain variance and noise floor as the control. No model is used.
              Run on the fresh worlds and also on the tuning worlds with seed 7 (compare with out/ml2/control_noise.csv).
If the rule gate matches the classifier version, ML is not needed in this structure; if it does not, the classifier earns its place.

  python sim/ml2_classifier_tests.py        output: out/ml2/classifier_tests.csv   (about 30-35 minutes, 4 workers)
"""
import multiprocessing as mp
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import ml2_fresh as F  # noqa: E402  (reuses TASKS and the condition list)
import ml2_noise_normal as N  # noqa: E402
import pipeline as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "ml2")
B = dict(ml2_mode="hard", ml2_terrain_R=True, ml2_noise_heuristic=True)
ACCEPT = "ablation: accept ALL flagged readings"
REJECT = "ablation: reject ALL flagged readings"
RULE = "non-ML rule gate (adaptive tolerance) instead of classifier"
FRESH_JUDGES = {ACCEPT: dict(B, ml2_threshold=1.01), REJECT: dict(B, ml2_threshold=-0.01), RULE: dict(B, ml2_rule_gate=True)}
TUNE_JUDGES = {RULE: dict(B, ml2_rule_gate=True)}
TASKS = [(wk, seed, group, FRESH_JUDGES) for wk, seed, group in F.TASKS] + \
        [(wk, 7, "C tuning worlds, seed 7", TUNE_JUDGES) for wk in [("proc", s) for s in P.TUNE_SEEDS] + [("site01", P.SUN_EL, P.SUN_AZ)]]


def task(spec):
    wk, seed, group, judges = spec
    w, tr = P.get_world(wk)
    clf = pickle.load(open(os.path.join(ROOT, "models", "fault_clf_v3.pkl"), "rb"))
    rows = []
    for cname, sc in N.CONDS.items():
        for jname, extra in judges.items():
            d = engine.Draws(w, sc, 100, seed)
            kw = dict(P.tuned()); kw["cam_policy"] = "conf"; kw.update(extra)
            r = engine.simulate(w, tr, sc, "ml2", d, ml_model=None if extra.get("ml2_rule_gate") else clf, **kw)
            rows.append(dict(group=group, world=str(wk[:2]), condition=cname, judge=jname, success=int(r["success"].sum()),
                             alt_rms=float(np.sqrt(r["alt_sq"].sum() / max(r["alt_n"].sum(), 1)))))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    P.warm(list(dict.fromkeys(t[0] for t in TASKS)))
    rows = []
    with mp.Pool(4) as pool:
        for r in pool.imap_unordered(task, TASKS):
            rows += r
            print("  done", r[0]["group"], r[0]["world"], flush=True)
    new = pd.DataFrame(rows)
    new.to_csv(os.path.join(OUT, "classifier_tests.csv"), index=False)
    pd.set_option("display.width", 260)
    fresh = pd.read_csv(os.path.join(OUT, "fresh.csv"))
    both = pd.concat([fresh, new[new.group != "C tuning worlds, seed 7"]])
    order = ["pitfal", "trust2", F.HEUR, ACCEPT, REJECT, RULE]
    t = both.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order].round(1)
    print("\nFRESH WORLDS, 7 world runs pooled (non-ML control = full classifier + running noise)\n", t.to_string(), flush=True)
    old = pd.read_csv(os.path.join(OUT, "noise_normal.csv"))
    ctl = pd.read_csv(os.path.join(OUT, "control_noise.csv"))
    c = pd.concat([old[old.judge.isin(["pitfal", "trust2"])], ctl, new[new.group == "C tuning worlds, seed 7"]])
    order2 = ["pitfal", "trust2", ctl.judge.iloc[0], RULE]
    t2 = c.pivot_table(index="condition", columns="judge", values="success").reindex(list(N.CONDS))[order2].round(1)
    print("\nTUNING WORLDS seed 7\n", t2.to_string(), flush=True)
    w = both.pivot_table(index=["group", "world", "condition"], columns="judge", values="success")
    print("\nFresh cells: rule gate minus full control: mean %.1f, positive in %d of %d cells" %
          ((w[RULE] - w[F.HEUR]).mean(), int(((w[RULE] - w[F.HEUR]) > 0).sum()), len(w)))


if __name__ == "__main__":
    mp.freeze_support()
    main()
