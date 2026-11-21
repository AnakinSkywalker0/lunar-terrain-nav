"""Verify frozen navigation-v3 records and summarize both frames and touchdown speed.

All inference is descriptive over the observed areas. Sensor tables describe
decisions at delivery; subsequent fixed-lag replay can re-evaluate earlier gates.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

THRESHOLDS = (10, 50, 100)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def booleans(series):
    values = series.astype(str).str.lower()
    require(values.isin(["true", "false"]).all(), f"Invalid boolean in {series.name}")
    return values == "true"


def score(contact, miss, vertical, horizontal, threshold):
    return (contact & np.isfinite(miss) & np.isfinite(vertical) & np.isfinite(horizontal)
            & (miss >= 0) & (miss < threshold) & (abs(vertical) < 2) & (horizontal >= 0) & (horizontal < 1))


def markdown(frame):
    headers = list(frame.columns)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False, name=None):
        rows.append("| " + " | ".join(f"{x:.3f}" if isinstance(x, (float, np.floating)) else str(x) for x in row) + " |")
    return "\n".join(rows)


def summarize(folder):
    folder = Path(folder).resolve()
    status = json.loads((folder / "status.json").read_text())
    require(status["state"] == "complete" and status["completed"] == status["expected"], "Incomplete Unity job")
    contracts = json.loads((folder / "contracts.json").read_text())
    require(contracts["passed"], "Navigation contracts failed")
    for line in (folder / "source_sha256.txt").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        require(hashlib.sha256((folder / relative).read_bytes()).hexdigest() == expected, f"Frozen artifact changed: {relative}")
    planned = json.loads((folder / "cases.json").read_text())["cases"]
    expected_ids = {f"{c['site']}_{c['condition']}_{c['altitude']}_{c['seed']}_{c['arm']}" for c in planned}
    runs = pd.read_csv(folder / "summary.csv")
    sensors = pd.read_csv(folder / "sensors.csv")
    require(len(runs) == status["expected"] and runs.id.is_unique and set(runs.id) == expected_ids, "Missing/duplicate/unexpected descents")
    require(not sensors.duplicated(["id", "kind", "sequence"]).any(), "Duplicate sensor receipts")
    require(set(sensors.id) == expected_ids, "Missing/unexpected sensor records")
    require(np.isfinite(runs.select_dtypes(include="number").to_numpy()).all(), "Nonfinite summary")
    require(np.isfinite(sensors.select_dtypes(include="number").to_numpy()).all(), "Nonfinite sensor record")
    require(((sensors.delivered_s - sensors.captured_s) >= -1e-5).all(), "Sensor delivered before capture")
    require((sensors.inflation.between(1, 4)).all(), "Unbounded ML influence")
    require(sensors.kind.isin(["Range", "Terrain"]).all(), "Unknown sensor kind")
    require(runs.termination.isin(["Contact", "Timeout", "OutsideTerrain"]).all(), "Unknown termination")
    contact = booleans(runs.contact)
    require((contact == runs.termination.eq("Contact")).all(), "Contact/termination mismatch")
    absolute = np.hypot(runs.x, runs.z)
    relative = np.hypot(runs.x-runs.shift_x, runs.z-runs.shift_z)
    require(np.allclose(absolute, runs.absolute_miss_m, atol=1e-4), "Absolute miss inconsistent")
    require(np.allclose(relative, runs.map_miss_m, atol=1e-4), "Map-target miss inconsistent")
    for prefix, miss in [("abs", absolute), ("map", relative)]:
        for threshold in THRESHOLDS:
            expected = score(contact, miss, runs.impact_vz, runs.impact_vh, threshold)
            require((expected == booleans(runs[f"{prefix}_{threshold}"])).all(), "Unity/Python success disagreement")
            runs[f"{prefix}_{threshold}"] = expected
    initial = []
    recovery = []
    for run in runs.itertuples():
        trace = pd.read_csv(folder / f"{run.id}.csv")
        require(len(trace) > 1 and np.isfinite(trace.select_dtypes(include="number").to_numpy()).all(), f"Invalid trajectory: {run.id}")
        require(trace.t.is_monotonic_increasing and abs(trace.t.iloc[-1]-run.time_s) < 1e-4, "Trajectory time mismatch")
        require(np.allclose(trace.iloc[-1][["x", "z"]].to_numpy(dtype=float), [run.x, run.z], atol=1e-5), "Contact point mismatch")
        known_altitude = booleans(trace.altitude_valid) if "altitude_valid" in trace else pd.Series(True, index=trace.index)
        require((trace.sigma_horizontal_m >= 0).all() and (trace.loc[known_altitude, "sigma_agl_m"] >= 0).all()
                and (trace.loc[~known_altitude, "sigma_agl_m"] == -1).all(), "Invalid uncertainty")
        require((trace.last_range_s <= trace.t+1e-5).all() and (trace.last_scan_s <= trace.t+1e-5).all(), "Future information leak")
        initial.append(dict(id=run.id, site=run.site, condition=run.condition, altitude=run.altitude, seed=run.seed,
                            **{k: trace.iloc[0][k] for k in ["x", "y", "z", "vx", "vy", "vz", "ex", "ey", "ez", "evx", "evy", "evz"]}))
        events = sensors[sensors.id == run.id]
        for kind, accepted_column, rejected_column, missing_column in [
            ("Range", "range_accepted", "range_rejected", "missing_ranges"),
            ("Terrain", "scan_accepted", "scan_rejected", "missing_scans")]:
            e = events[events.kind == kind]
            accepted = e.decision.eq("Accepted").sum()
            missing = e.decision.isin(["NoReturn", "Unavailable", "BelowScanEnvelope"]).sum()
            require(accepted == getattr(run, accepted_column) and missing == getattr(run, missing_column)
                    and len(e)-accepted-missing == getattr(run, rejected_column), "Sensor accounting mismatch")
        if run.arm != "ml_terminal":
            require((events.inflation == 1).all() and (events.ml_prediction == -1).all(), "Classical arm evaluated ML")
        if run.condition in ("range_dropout", "range_spike", "scan_dropout"):
            kind = "Terrain" if run.condition == "scan_dropout" else "Range"
            end = {"range_dropout": 22, "range_spike": 18, "scan_dropout": 24}[run.condition]
            reacquired = events[(events.kind == kind) & (events.captured_s >= end) & events.decision.eq("Accepted")]
            recovery.append(dict(id=run.id, condition=run.condition, arm=run.arm,
                                 recovered=not reacquired.empty,
                                 first_valid_after_fault_s=float(reacquired.delivered_s.min()) if len(reacquired) else -1))
    initial = pd.DataFrame(initial)
    for _, group in initial.groupby(["site", "condition", "altitude", "seed"]):
        require(len(group) == 3, "Incomplete three-arm pairing")
        require((group.drop(columns=["id", "site", "condition", "altitude", "seed"]).nunique() == 1).all(), "Unmatched initial conditions")
    runs["speed_violation"] = contact & ((runs.impact_vz.abs() >= 2) | (runs.impact_vh >= 1))
    records = []
    for (condition, arm), group in runs.groupby(["condition", "arm"]):
        row = dict(condition=condition, arm=arm, n=len(group), contacts=int(booleans(group.contact).sum()),
                   mean_abs_m=group.absolute_miss_m.mean(), mean_map_m=group.map_miss_m.mean(),
                   speed_violations=int(group.speed_violation.sum()))
        for frame in ["abs", "map"]:
            for t in THRESHOLDS:
                row[f"{frame}_{t}_count"] = int(group[f"{frame}_{t}"].sum())
                row[f"{frame}_{t}_rate"] = group[f"{frame}_{t}"].mean()
        records.append(row)
    table = pd.DataFrame(records)
    overall = runs.groupby("arm").agg(n=("id", "size"), mean_abs_m=("absolute_miss_m", "mean"),
                                      mean_map_m=("map_miss_m", "mean"), map_10_count=("map_10", "sum"),
                                      map_50_count=("map_50", "sum"), speed_violations=("speed_violation", "sum")).reset_index()
    area = runs.groupby(["site", "condition", "arm"]).agg(n=("id", "size"), mean_map_m=("map_miss_m", "mean"),
                                                           map_10_rate=("map_10", "mean"), speed_violations=("speed_violation", "sum")).reset_index()
    pairs = runs.pivot(index=["site", "condition", "altitude", "seed"], columns="arm", values=["map_miss_m", "speed_violation", "map_10"])
    paired = pairs.index.to_frame(index=False)
    for metric in ["map_miss_m", "speed_violation", "map_10"]:
        paired[f"ml_minus_classical_{metric}"] = (pairs[metric]["ml_terminal"].astype(float)-pairs[metric]["classical_terminal"].astype(float)).to_numpy()
    sensor_groups = []
    with_arms = sensors.merge(runs[["id", "arm", "condition"]], on="id", validate="many_to_one")
    for (condition, arm), group in with_arms[with_arms.kind.eq("Range")].groupby(["condition", "arm"]):
        fault = booleans(group.injected_fault)
        valid = ~group.decision.isin(["Unavailable", "NoReturn"])
        faulty = group[fault & valid]; healthy = group[~fault & valid]
        sensor_groups.append(dict(condition=condition, arm=arm, faulty_receipts=len(faulty),
                                  faulty_accepted=int(faulty.decision.eq("Accepted").sum()), healthy_receipts=len(healthy),
                                  healthy_innovation_rejections=int(healthy.decision.eq("InnovationRejected").sum())))
    dest = folder / "analysis"
    dest.mkdir(exist_ok=True)
    table.to_csv(dest / "conditions.csv", index=False)
    overall.to_csv(dest / "overall.csv", index=False)
    area.to_csv(dest / "areas.csv", index=False)
    paired.to_csv(dest / "paired.csv", index=False)
    pd.DataFrame(sensor_groups).to_csv(dest / "range_decisions.csv", index=False)
    pd.DataFrame(recovery).to_csv(dest / "recovery.csv", index=False)
    report = dict(passed=True, descents=len(runs), sensor_receipts=len(sensors), terrain_areas=runs.site.nunique(),
                  contracts=contracts["checks"], checks=["frozen artifact hashes", "complete paired cases", "finite trajectories and receipts",
                  "timestamp ordering", "initial condition parity", "ML routing/bounds", "sensor accounting", "physical contact and both-frame scoring"])
    (dest / "verification.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    columns = ["condition", "arm", "n", "mean_abs_m", "mean_map_m", "speed_violations", "map_10_count", "map_50_count", "map_100_count"]
    text = ("# Navigation v3: verified recorded outcomes\n\n"
            f"{len(runs)} descents, {len(sensors)} sensor receipts, {runs.site.nunique()} observed terrain areas.\n\n"
            "Descriptive engineering validation; no independent-site confidence or flight-reliability claim.\n"
            "Source-map uncertainty scales a synthetic correlated error proxy, not PGDA clones.\n"
            "Success requires actual contact, distance below the indicated threshold, vertical speed <2 m/s and lateral speed <1 m/s.\n\n"
            + markdown(overall) + "\n\n" + markdown(table[columns]) + "\n\n"
            "Full counts and rates in both frames: `conditions.csv`. Area-level results: `areas.csv`.\n"
            "Paired ML-minus-classical differences: `paired.csv`. Sensor receipt-time decisions: `range_decisions.csv`.\n"
            "Outage/fault recovery: `recovery.csv`. Replay can revise historical update decisions.\n")
    (dest / "REPORT.md").write_text(text, encoding="utf-8")
    print(markdown(overall))
    print(markdown(table[columns]))
    print(json.dumps({k: report[k] for k in ("passed", "descents", "sensor_receipts", "terrain_areas")}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    summarize(parser.parse_args().folder)
