"""Plots and tables from out/mc results."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "mc")
PL = os.path.join(ROOT, "out", "plots")
os.makedirs(PL, exist_ok=True)

NAMES = {"fixed": "Fixed gate", "pitfal": "PITFAL-style", "tolerance": "Map tolerance", "wait": "Wait and see",
         "second": "Second opinion", "ml": "ML classifier", "trust": "Trust v1 (4-step)", "trust2": "Trust v2", "trust2_scan": "Trust v2 + live scan", "trust_scan": "Trust + live scan",
         "trust_nocam": "ablation: no camera step", "trust_noprob": "ablation: no probation", "trust_nophys": "ablation: no physical check"}
COL = {"fixed": "#d9534f", "pitfal": "#f0ad4e", "tolerance": "#8c6bb1", "wait": "#5bc0de", "second": "#999999", "ml": "#5cb85c",
       "trust": "#6aa57f", "trust2": "#1f6f43", "trust2_scan": "#0b3d91", "trust_scan": "#0b3d91", "trust_nocam": "#cfcfcf", "trust_noprob": "#bdbdbd", "trust_nophys": "#adadad"}


def main_plots():
    df = pd.read_csv(os.path.join(OUT, "main_results.csv"))
    scen = list(dict.fromkeys(df.scenario))
    judges = ["fixed", "pitfal", "tolerance", "wait", "second", "ml", "trust", "trust2", "trust2_scan"]
    fig, axs = plt.subplots(1, len(scen), figsize=(4 * len(scen), 4.6), sharey=True)
    for ax, s in zip(np.atleast_1d(axs), scen):
        d = df[df.scenario == s].set_index("judge")
        x = np.arange(len(judges))
        v = [d.loc[j, "success_pct"] for j in judges]
        lo = [d.loc[j, "success_pct"] - d.loc[j, "success_lo"] for j in judges]
        hi = [d.loc[j, "success_hi"] - d.loc[j, "success_pct"] for j in judges]
        ax.bar(x, v, yerr=[lo, hi], color=[COL[j] for j in judges], capsize=3)
        ax.set_xticks(x); ax.set_xticklabels([NAMES[j] for j in judges], rotation=60, ha="right", fontsize=8)
        ax.set_title(s, fontsize=9); ax.set_ylim(0, 105)
    np.atleast_1d(axs)[0].set_ylabel("Landing success (%), 95% interval")
    fig.suptitle("Round 2: landing success on Site04 (unseen site), 500 runs per cell, same confidence-gated camera for every judge", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(PL, "01_success_by_scenario.png"), dpi=130); plt.close(fig)

    # error trade-off: false rejection vs missed faults
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, s in zip(axs, ["cliff + faults", "shadow + noisy altimeter (IM-2)"]):
        d = df[df.scenario == s].set_index("judge")
        for j in judges:
            ax.scatter(d.loc[j, "false_rej_pct"], d.loc[j, "missed_fault_pct"], s=90, color=COL[j], label=NAMES[j], edgecolor="k")
        ax.set_xlabel("Valid readings wrongly rejected (%)"); ax.set_ylabel("Faulty readings wrongly believed (%)")
        ax.set_title(s, fontsize=10); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.suptitle("Both mistakes counted (down-and-left is better)", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(PL, "02_two_mistakes.png"), dpi=130); plt.close(fig)

    # markdown table
    cols = ["success_pct", "success_lo", "success_hi", "alt_rms_m", "false_rej_pct", "missed_fault_pct", "cam_weight_in_shadow", "fuel_left_landed_kg"]
    with open(os.path.join(OUT, "main_results.md"), "w") as f:
        for s in scen:
            f.write(f"\n### {s}\n\n| judge | success % | 95% CI | alt RMS m | false rej % | missed fault % | cam weight in shadow | fuel left (landed) kg |\n|---|---|---|---|---|---|---|---|\n")
            d = df[df.scenario == s].set_index("judge")
            for j in judges + ["trust_noprob", "trust_nophys"]:
                r = d.loc[j]
                f.write(f"| {NAMES[j]} | {r.success_pct:.1f} | {r.success_lo:.0f}-{r.success_hi:.0f} | {r.alt_rms_m:.0f} | {r.false_rej_pct:.1f} | {r.missed_fault_pct:.1f} | {r.cam_weight_in_shadow:.2f} | {r.fuel_left_landed_kg:.0f} |\n")


def sweep_plots():
    pa = os.path.join(OUT, "sweeps_a.csv")
    if os.path.exists(pa):
        a = pd.read_csv(pa)
        h = a
        fig, ax = plt.subplots(figsize=(6, 4))
        for j in ("pitfal", "trust2"):
            d = h[h.judge == j].sort_values("value")
            ax.errorbar(d.value.astype(float), d.success_pct, yerr=[d.success_pct - d.success_lo, d.success_hi - d.success_pct], marker="o", color=COL[j], label=NAMES[j], capsize=3)
        ax.set_xscale("log"); ax.set_xlabel("Initial horizontal position uncertainty (m)"); ax.set_ylabel("Landing success (%)")
        ax.set_title("When does the trust layer help? (cliff scenario, Site04)"); ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(PL, "03_when_does_it_help.png"), dpi=130); plt.close(fig)
    ps = os.path.join(OUT, "sweeps_sun.csv")
    if os.path.exists(ps):
        s = pd.read_csv(ps)
        s['value'] = s.tag.str[4:]
        fig, ax = plt.subplots(figsize=(8, 4))
        keys = list(dict.fromkeys(s.value))
        x = np.arange(len(keys)); wd = 0.38
        for i, j in enumerate(("pitfal", "trust2")):
            d = s[s.judge == j].set_index("value").loc[keys]
            ax.bar(x + (i - 0.5) * wd, d.success_pct, wd, color=COL[j], label=NAMES[j])
        ax.set_xticks(x); ax.set_xticklabels(keys, rotation=45, ha="right", fontsize=8); ax.set_ylabel("Landing success (%)")
        ax.set_title("Lighting sweep: Sun elevation and azimuth (shadow + noisy altimeter)"); ax.legend(); ax.grid(axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(os.path.join(PL, "04_lighting_sweep.png"), dpi=130); plt.close(fig)


def replay_plot():
    rd = os.path.join(ROOT, "out", "replay")
    if not os.path.exists(os.path.join(rd, "replay_trust2.csv")):
        return
    fig, axs = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for j, c in (("fixed", "#d9534f"), ("pitfal", "#f0ad4e"), ("trust2", "#1f6f43")):
        d = pd.read_csv(os.path.join(rd, f"replay_{j}.csv"))
        axs[0].plot(d.t, d.agl_est - d.agl_true, color=c, label=NAMES[j])
        axs[1].plot(d.t, d.agl_true, color=c, label=NAMES[j])
    axs[0].set_ylabel("Estimated minus true altitude (m)"); axs[0].legend(); axs[0].grid(alpha=0.3)
    axs[1].set_ylabel("True altitude above ground (m)"); axs[1].set_xlabel("time (s)"); axs[1].set_yscale("symlog"); axs[1].grid(alpha=0.3)
    fig.suptitle("One replayed descent (cliff + faults): same noise and faults for every method")
    fig.tight_layout(); fig.savefig(os.path.join(PL, "05_replay_altitude.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    for f in (main_plots, sweep_plots, replay_plot):
        try:
            f()
        except FileNotFoundError as e:
            print("skip", f.__name__, e)
