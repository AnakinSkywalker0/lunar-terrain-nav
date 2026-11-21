"""Figure for the report: Site04 landing success versus altimeter noise, round 3 (data: out/round3/site04.csv)."""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(ROOT, "out", "round3", "site04.csv"))
df = df[df.label == "aware"]
conds = ["cliff + faults (nominal noise)", "x2 below 6000 m", "x4 below 6000 m", "x8 below 6000 m (TRAINING)", "x16 below 6000 m"]
labels = ["nominal", "x2", "x4", "x8", "x16"]
series = [("tolerance + noise floor", "Tolerance + noise floor (new)", "#1b7837", "o", "-"),
          ("trust2", "Trust v2", "#2166ac", "s", "-"),
          ("pitfal", "PITFAL-style", "#e08214", "^", "-"),
          ("tolerance", "Tolerance (before)", "#762a83", "v", "--")]
fig, ax = plt.subplots(figsize=(7.4, 3.9), dpi=200)
for cfg, name, col, mk, ls in series:
    y = [df[(df.condition == c) & (df.config == cfg)].success_pct.iloc[0] for c in conds]
    ax.plot(labels, y, color=col, marker=mk, linestyle=ls, linewidth=2, markersize=6, label=name)
ax.set_ylim(0, 105)
ax.set_xlabel("Altimeter noise (multiple of normal)")
ax.set_ylabel("Landings that succeed (%)")
ax.grid(axis="y", alpha=0.3)
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs", "round3_noise.png"))
