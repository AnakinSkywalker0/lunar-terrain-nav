"""Analyse guidance-ablation runs by terrain area (the independent unit), per the written protocol.

Usage: python tools/analyze_guidance_ablation.py <out_dir> <run_folder> [<run_folder> ...]
Reads summary.csv and each descent's trace (last row = contact position). Writes tables, a JSON
summary and figures to <out_dir>. Decision rules are those in docs/GUIDANCE_ABLATION_PROTOCOL.md.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

SHIFT = {"map_shift": (22.0, -31.0), "tie3": (2.12, 2.12), "tie8": (5.66, 5.66)}
THRESHOLDS = (10, 50, 100)
GUIDANCE = ["baseline", "terminal", "braking"]
ARMS = ["off", "geometric", "bounded", "utility", "authority"]
CONDITIONS = ["aligned", "tie3", "tie8", "map_shift", "relief_positive"]
RNG = np.random.default_rng(20261108)


def last_xz(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 600))
        line = f.read().decode().strip().splitlines()[-1]
    p = line.split(",")
    return float(p[1]), float(p[3])


def load(folders):
    frames = []
    for folder in map(Path, folders):
        r = pd.read_csv(folder / "summary.csv")
        r["run"] = folder.name
        xz = np.array([last_xz(folder / f"{i}.csv") for i in r.id])
        r["x"], r["z"] = xz[:, 0], xz[:, 1]
        frames.append(r)
    r = pd.concat(frames, ignore_index=True)
    r["guidance"] = r.id.str.extract(r"_g([a-z]+)_")[0]
    r["area"] = r.site_id
    sx = r.condition.map(lambda c: SHIFT.get(c, (0, 0))[0])
    sz = r.condition.map(lambda c: SHIFT.get(c, (0, 0))[1])
    r["map_miss"] = np.hypot(r.x - sx, r.z - sz)
    contact = r.touchdown.astype(bool)
    drift = (np.hypot(r.x, r.z) - r.target_miss_m)[contact].abs().max()
    assert drift < 0.05, f"recomputed miss differs from recorded by {drift}"
    r["contact"] = contact
    r["violation"] = contact & ((r.impact_vz >= 2) | (r.impact_vh >= 1))
    r["noncontact"] = ~contact
    for t in THRESHOLDS:
        ok = contact & (r.impact_vz < 2) & (r.impact_vh < 1)
        r[f"map_ok_{t}"] = ok & (r.map_miss < t)
        r[f"abs_ok_{t}"] = ok & (r.target_miss_m < t)
    return r


def per_area(r):
    g = r.groupby(["area", "condition", "guidance", "arm"], sort=False)
    return g.agg(n=("id", "size"), violation=("violation", "mean"), noncontact=("noncontact", "mean"),
                 map_miss=("map_miss", "mean"), abs_miss=("target_miss_m", "mean"),
                 map_ok_10=("map_ok_10", "mean"), map_ok_50=("map_ok_50", "mean"),
                 map_ok_100=("map_ok_100", "mean"), abs_ok_10=("abs_ok_10", "mean")).reset_index()


def boot_ci(diffs, n=10000):
    diffs = np.asarray(diffs, float)
    means = RNG.choice(diffs, size=(n, len(diffs)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def compare(pa, cond, arm_a, g_a, arm_b, g_b, metric="violation"):
    a = pa[(pa.condition == cond) & (pa.arm == arm_a) & (pa.guidance == g_a)].set_index("area")[metric]
    b = pa[(pa.condition == cond) & (pa.arm == arm_b) & (pa.guidance == g_b)].set_index("area")[metric]
    d = (a - b).dropna()  # positive = A worse (higher) than B
    lower = int((d < 0).sum()); higher = int((d > 0).sum())
    nonzero = lower + higher
    p = stats.binomtest(lower, nonzero, 0.5).pvalue if nonzero else 1.0
    lo, hi = boot_ci(d) if len(d) else (np.nan, np.nan)
    return dict(condition=cond, a=f"{arm_a}/{g_a}", b=f"{arm_b}/{g_b}", metric=metric, n_areas=len(d),
                mean_a=float(a.mean()), mean_b=float(b.mean()), median_a=float(a.median()), median_b=float(b.median()),
                areas_a_lower=lower, areas_a_higher=higher, sign_test_p=float(p),
                mean_diff_a_minus_b=float(d.mean()), boot95=(lo, hi))


def main(out_dir, folders):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    r = load(folders)
    pa = per_area(r)
    pa.to_csv(out / "per_area.csv", index=False)
    r.drop(columns=["x", "z"]).to_csv(out / "per_run.csv", index=False)
    n_areas = r.area.nunique()

    # Table 1: pooled-over-areas means of per-area rates (area is the unit)
    t1 = pa.groupby(["condition", "guidance", "arm"], sort=False).agg(
        areas=("area", "nunique"), violation=("violation", "mean"), noncontact=("noncontact", "mean"),
        map_miss=("map_miss", "mean"), abs_miss=("abs_miss", "mean"),
        map_ok_10=("map_ok_10", "mean"), map_ok_50=("map_ok_50", "mean"), abs_ok_10=("abs_ok_10", "mean")).reset_index()
    t1.to_csv(out / "table_by_condition_guidance_arm.csv", index=False)

    # G1: does better guidance remove violations? geometric arm, conditions with corrections that go wrong/shift
    g1 = []
    for cond in ["relief_positive", "map_shift", "tie8", "tie3", "aligned"]:
        for g in ["terminal", "braking"]:
            for arm in ["geometric", "utility"]:
                g1.append(compare(pa, cond, arm, g, arm, "baseline"))
    pd.DataFrame(g1).to_csv(out / "g1_guidance_vs_baseline.csv", index=False)

    def verdict_g1(cond, g, arm="geometric"):
        row = next(x for x in g1 if x["condition"] == cond and x["a"] == f"{arm}/{g}")
        base = row["median_b"]; new = row["median_a"]
        if base <= 0:
            return "no violations at baseline", row
        red = 1 - new / base
        label = "artifact (>=50% fewer)" if red >= 0.5 else ("persists (<20% fewer)" if red < 0.2 else "mixed")
        return f"{label}; median per-area violation {base:.2f} -> {new:.2f} ({red:+.0%})", row

    # G2: authority gate under baseline guidance
    g2 = [compare(pa, c, "authority", "baseline", "geometric", "baseline", m)
          for c in CONDITIONS for m in ("violation", "map_miss", "map_ok_10")]
    pd.DataFrame(g2).to_csv(out / "g2_authority_vs_geometric.csv", index=False)
    g2v = [x for x in g2 if x["metric"] == "violation" and x["condition"] in ("relief_positive", "map_shift", "tie8")]
    # also vs bounded and utility, any condition, for completeness
    g2b = [compare(pa, c, "authority", "baseline", a, "baseline", m)
           for c in CONDITIONS for a in ("bounded", "utility", "off") for m in ("violation", "map_miss")]
    pd.DataFrame(g2b).to_csv(out / "g2_authority_vs_other_arms.csv", index=False)

    summary = {"areas": int(n_areas), "descents": int(len(r)),
               "g1": {f"{c}/{g}/{a}": verdict_g1(c, g, a)[0]
                      for c in ["relief_positive", "map_shift", "tie8"] for g in ["terminal", "braking"] for a in ["geometric", "utility"]},
               "g2_violation": {x["condition"]: dict(authority=x["mean_a"], geometric=x["mean_b"],
                                                     areas_authority_lower=x["areas_a_lower"], areas_authority_higher=x["areas_a_higher"],
                                                     p=x["sign_test_p"]) for x in g2v}}
    # G2 verdict per protocol: violations fall in >=10 of 12 areas AND map miss not worse by >10% (pooled over the conditions listed)
    ok_viol = all(x["areas_a_lower"] >= 10 for x in g2v) if n_areas >= 12 else False
    miss = [x for x in g2 if x["metric"] == "map_miss" and x["condition"] in ("relief_positive", "map_shift", "tie8")]
    ok_miss = all(x["mean_a"] <= 1.10 * x["mean_b"] for x in miss)
    summary["g2_supported"] = bool(ok_viol and ok_miss)
    summary["g2_detail"] = {"violations_fall_in_>=10_of_12_areas_all_conditions": bool(ok_viol), "map_miss_not_worse_10pct": bool(ok_miss)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    # Figures
    fig, axes = plt.subplots(1, 5, figsize=(20, 4), sharey=True)
    width = 0.27
    for ax, cond in zip(axes, CONDITIONS):
        for k, g in enumerate(GUIDANCE):
            vals = [pa[(pa.condition == cond) & (pa.guidance == g) & (pa.arm == a)].violation.mean() for a in ARMS]
            ax.bar(np.arange(len(ARMS)) + (k - 1) * width, vals, width, label=g)
        ax.set_xticks(range(len(ARMS))); ax.set_xticklabels(ARMS, rotation=30)
        ax.set_title(cond)
    axes[0].set_ylabel("speed-violation rate\n(mean over areas)"); axes[0].legend(title="guidance")
    fig.suptitle(f"Touchdown speed violations by guidance and correction rule ({n_areas} areas)")
    fig.tight_layout(); fig.savefig(out / "fig_violations.png", dpi=130); plt.close(fig)

    fig, axes = plt.subplots(1, 5, figsize=(20, 4), sharey=True)
    for ax, cond in zip(axes, CONDITIONS):
        for k, g in enumerate(GUIDANCE):
            vals = [pa[(pa.condition == cond) & (pa.guidance == g) & (pa.arm == a)].map_ok_10.mean() for a in ARMS]
            ax.bar(np.arange(len(ARMS)) + (k - 1) * width, vals, width, label=g)
        ax.set_xticks(range(len(ARMS))); ax.set_xticklabels(ARMS, rotation=30); ax.set_title(cond)
    axes[0].set_ylabel("success: map-frame miss < 10 m,\nvz<2, vh<1 (mean over areas)"); axes[0].legend(title="guidance")
    fig.tight_layout(); fig.savefig(out / "fig_success_map10.png", dpi=130); plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
