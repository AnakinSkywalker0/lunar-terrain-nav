"""Analyse the unmodelled-relief amplitude sweep (stage eval_sweep): where does correcting stop helping?

Usage: python tools/analyze_relief_sweep.py <out_dir> <run_folder> [...]
Unit of analysis is the terrain area. Amplitude 0 = aligned control. The shaded band marks the
0.3-0.5 m per-pixel height RMS reported for the PGDA DEMs in the 29 Oct literature note (Barker et al.;
taken from that note, not re-verified).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_guidance_ablation import load, per_area, boot_ci  # noqa: E402

ARMS = ["off", "geometric", "bounded", "authority", "kf_chi2", "utility"]


def amp(cond):
    return 0.0 if cond == "aligned" else float(cond.replace("relief_a", ""))


def main(out_dir, folders):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    r = load(folders)
    r = r[r.condition.str.startswith("relief_a") | (r.condition == "aligned")].copy()
    r["amp"] = r.condition.map(amp)
    pa = r.groupby(["area", "amp", "arm"]).agg(
        n=("id", "size"), miss=("map_miss", "mean"), violation=("violation", "mean"),
        ok10=("map_ok_10", "mean"), ok50=("map_ok_50", "mean")).reset_index()
    pa.to_csv(out / "sweep_per_area.csv", index=False)
    agg = pa.groupby(["amp", "arm"]).agg(areas=("area", "nunique"), miss=("miss", "mean"), miss_lo=("miss", "min"),
                                        miss_hi=("miss", "max"), violation=("violation", "mean"),
                                        ok10=("ok10", "mean"), ok50=("ok50", "mean")).reset_index()
    agg.to_csv(out / "sweep_by_amplitude_arm.csv", index=False)

    # Paired vs doing nothing ("off"): in how many areas is the arm's miss lower / its violation rate higher?
    rows = []
    for a in sorted(pa.amp.unique()):
        off = pa[(pa.amp == a) & (pa.arm == "off")].set_index("area")
        for arm in ARMS[1:]:
            x = pa[(pa.amp == a) & (pa.arm == arm)].set_index("area")
            d_miss = (x.miss - off.miss).dropna()
            d_vio = (x.violation - off.violation).dropna()
            better = int((d_miss < 0).sum()); worse = int((d_miss > 0).sum())
            p = stats.binomtest(better, better + worse, 0.5).pvalue if better + worse else 1.0
            lo, hi = boot_ci(d_miss) if len(d_miss) else (np.nan, np.nan)
            rows.append(dict(amp=a, arm=arm, areas=len(d_miss), mean_miss_change_vs_off=float(d_miss.mean()),
                             boot95_lo=lo, boot95_hi=hi, areas_miss_lower=better, areas_miss_higher=worse,
                             sign_p=float(p), mean_violation_vs_off=float(d_vio.mean())))
    paired = pd.DataFrame(rows)
    paired.to_csv(out / "sweep_paired_vs_off.csv", index=False)

    # Break-even: smallest amplitude at which the arm's mean miss is no better than doing nothing, and
    # smallest at which its mean violation rate exceeds 5% (pooled over areas).
    be = {}
    for arm in ARMS[1:]:
        sub = paired[paired.arm == arm].sort_values("amp")
        worse_miss = sub[sub.mean_miss_change_vs_off >= 0]
        viol = agg[(agg.arm == arm) & (agg.violation > 0.05)].sort_values("amp")
        be[arm] = dict(first_amp_no_better_than_off=None if worse_miss.empty else float(worse_miss.amp.iloc[0]),
                       first_amp_violation_over_5pct=None if viol.empty else float(viol.amp.iloc[0]))
    (out / "sweep_breakeven.json").write_text(json.dumps(be, indent=2))

    xs = lambda a: np.where(np.asarray(a) == 0, 0.25, a)  # noqa: E731  (plot aligned at 0.25 m on a log axis)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.2))
    for arm in ARMS:
        s = agg[agg.arm == arm].sort_values("amp")
        axes[0].plot(xs(s.amp), s.miss, marker="o", label=arm)
        axes[1].plot(xs(s.amp), s.violation, marker="o", label=arm)
        axes[2].plot(xs(s.amp), s.ok10, marker="o", label=arm)
    for ax, yl in zip(axes, ["mean miss (m, map frame)", "speed-violation rate", "success (miss<10 m, vz<2, vh<1)"]):
        ax.set_xscale("log"); ax.set_xlabel("unmodelled relief amplitude (m); leftmost = aligned")
        ax.axvspan(0.3, 0.5, color="gray", alpha=0.25); ax.set_ylabel(yl)
    axes[0].set_yscale("log"); axes[0].legend(fontsize=8)
    fig.suptitle(f"How much unmodelled relief can a terrain correction tolerate? ({pa.area.nunique()} areas; gray = reported DEM height RMS)")
    fig.tight_layout(); fig.savefig(out / "fig_relief_sweep.png", dpi=130)
    pd.set_option("display.width", 220)
    print(agg.round(3).to_string(index=False)); print(json.dumps(be, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
