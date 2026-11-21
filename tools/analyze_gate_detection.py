"""Detection statistics of each correction rule, from the per-scan log (scans.csv) of a run folder.

Only scans the matcher itself accepted are considered (the rules decide what to do with those).
A proposed fix is
  wrong     if the corrected estimate would be > 10 m from the truth (the logged `wrong` flag),
  harmful   if it would leave the estimate farther from the truth than before (proposed_error_m > before_error_m + 1 m),
  useful    if it would improve the estimate by more than 1 m.
For each rule: missed-detection rate = share of wrong (or harmful) fixes that were applied (gain > 0);
false-alarm rate = share of useful fixes that were blocked entirely (gain == 0). `applied_mean_gain` is the mean fraction applied.
Usage: python tools/analyze_gate_detection.py <out_dir> <run_folder>
"""
import sys
from pathlib import Path

import pandas as pd


def main(out_dir, folder):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(Path(folder) / "scans.csv", usecols=["id", "accepted", "applied", "applied_gain", "before_error_m",
                                                         "proposed_error_m", "wrong", "arm"])
    s = s[s.accepted.astype(bool)].copy()
    s["condition"] = s.id.str.extract(r"_(aligned|tie3|tie8|map_shift|relief_positive|relief_a[0-9.]+)_v")[0]
    s["wrong"] = s.wrong.astype(bool)
    s["harmful"] = s.proposed_error_m > s.before_error_m + 1
    s["useful"] = s.proposed_error_m < s.before_error_m - 1
    s["applied"] = s.applied.astype(bool)
    rows = []
    for (cond, arm), g in s.groupby(["condition", "arm"]):
        w, h, u = g[g.wrong], g[g.harmful], g[g.useful]
        rows.append(dict(condition=cond, arm=arm, proposals=len(g), wrong_share=len(w) / len(g),
                         harmful_share=len(h) / len(g), missed_wrong=w.applied.mean() if len(w) else float("nan"),
                         missed_harmful=h.applied.mean() if len(h) else float("nan"),
                         false_alarm_useful=(~u.applied).mean() if len(u) else float("nan"),
                         applied_mean_gain=g.applied_gain.mean()))
    t = pd.DataFrame(rows)
    t.to_csv(out / "gate_detection.csv", index=False)
    pd.set_option("display.width", 220)
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
