"""Prepare grouped scan-trust data and audit the existing gate. NEVER trains.

Features and truth labels are separate files. All rows from a terrain area stay
in one development split, including paired OFF/ON runs and stationary scans.
These historical areas have already been inspected; this is NOT a pristine test.
"""
import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.scan_trust import FEATURES, TASK, ScanTrustGate, features_from_match

SITE_SPLIT = {"original": "train", "area01": "train", "area02": "train",
              "area03": "validation", "area04": "retrospective_test"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boolean(value):
    if value not in ("True", "False"):
        raise ValueError(f"Invalid boolean {value!r}")
    return value == "True"


def snapshot_sources(output):
    snapshots = output / "source_snapshot"
    snapshots.mkdir(exist_ok=True)
    files = ("sim/scan_trust.py", "tools/prepare_scan_trust_data.py", "tests/test_scan_trust.py")
    for name in files:
        shutil.copyfile(ROOT / name, snapshots / Path(name).name)
    return {name: sha(ROOT / name) for name in files}


def prepare(source, output):
    if not (source / "status.txt").read_text().startswith("Complete;"):
        raise ValueError("Source run is incomplete")
    output.mkdir(parents=True, exist_ok=False)
    with (source / "summary.csv").open(newline="") as f:
        cases = list(csv.DictReader(f))
    by_id = {row["id"]: row for row in cases}
    if len(by_id) != len(cases) or {r["site_id"] for r in cases} != set(SITE_SPLIT):
        raise ValueError("Expected unique cases and the five expanded areas")

    counts, splits = Counter(), Counter()
    audit = defaultdict(Counter)
    sample_ids, group_splits = set(), {}
    gate = ScanTrustGate()  # Explicitly no model; never imports sklearn or pickle.
    with ((source / "scans.csv").open(newline="") as inp,
          (output / "features.csv").open("w", newline="") as fx,
          (output / "labels.csv").open("w", newline="") as fy,
          (output / "groups.csv").open("w", newline="") as fg,
          (output / "shadow_decisions.csv").open("w", newline="") as fd):
        x, y, g, d = map(csv.writer, (fx, fy, fg, fd))
        x.writerow(("sample_id",) + FEATURES)
        y.writerow(("sample_id", "bad_match", "beneficial_by_over_1m",
                    "before_error_m", "proposed_error_m"))
        g.writerow(("sample_id", "split", "site_id", "pair_group", "run_id",
                    "kind", "condition", "altitude", "seed", "error_id", "matching", "time_s"))
        d.writerow(("sample_id", "geometric_accept", "trust_accept", "reason"))
        for line, row in enumerate(csv.DictReader(inp), 2):
            case = by_id[row["id"]]
            counts["source_scans"] += 1
            values = features_from_match(row)
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f"Nonfinite matcher feature at scan line {line}")
            valid, accepted = boolean(row["valid"]), boolean(row["accepted"])
            decision = gate.decide(values, valid=valid, geometric_accept=accepted)
            if decision.accept != (valid and accepted):
                raise AssertionError("No-model gate changed baseline acceptance")
            if accepted and not valid:
                raise ValueError("Accepted scan is invalid")
            if not valid:
                counts["excluded_invalid_scans"] += 1
                continue
            sample = f'{row["id"]}@{row["time_s"]}'
            if sample in sample_ids:
                raise ValueError(f"Duplicate scan sample {sample}")
            sample_ids.add(sample)
            before, proposed = float(row["before_error_m"]), float(row["proposed_error_m"])
            if not all(math.isfinite(v) and v >= 0 for v in (before, proposed)):
                raise ValueError("Invalid truth label source")
            bad = proposed > 10.0  # Defined for ALL valid proposals, not just accepted ones.
            if boolean(row["wrong"]) != (accepted and bad):
                raise ValueError("Archived wrong flag disagrees with recomputed truth label")
            split = SITE_SPLIT[case["site_id"]]
            pair = ":".join(case[k] for k in ("site_id", "condition", "altitude", "error_id", "seed"))
            if pair in group_splits and group_splits[pair] != split:
                raise AssertionError("Paired rows leaked across splits")
            group_splits[pair] = split
            x.writerow((sample,) + values)
            y.writerow((sample, int(bad), int(before - proposed > 1), before, proposed))
            g.writerow((sample, split, case["site_id"], pair, case["id"], case["kind"],
                        case["condition"], case["altitude"], case["seed"], case["error_id"],
                        case["matching"], row["time_s"]))
            d.writerow((sample, accepted, decision.accept, decision.reason))
            counts["valid_examples"] += 1
            counts["bad_examples"] += int(bad)
            splits[split] += 1
            for key in ("all", case["condition"], "site:" + case["site_id"]):
                a = audit[key]
                a["valid_proposals"] += 1
                a["bad_proposals"] += int(bad)
                a["accepted"] += int(accepted)
                a["accepted_bad"] += int(accepted and bad)
                a["rejected_safe"] += int(not accepted and not bad)
                a["safe_proposals"] += int(not bad)

    provenance = {name: sha(source / name) for name in
                  ("summary.csv", "scans.csv", "TerrainNavigationCore.cs", "ShortDescentExperiment.cs")}
    manifest = dict(task=TASK, features=list(FEATURES), label="int(proposed_horizontal_error_m > 10)",
                    source=str(source.resolve()), source_sha256=provenance,
                    training_performed=False, learned_model_loaded=False,
                    live_unity_integration=False, feature_schema_version=1,
                    site_split=SITE_SPLIT, counts=dict(counts), split_counts=dict(splits),
                    split_caveat="Retrospective development only: all five areas were already inspected. "
                                 "Fresh independent terrain and new offset patterns required for final evaluation.",
                    unit_of_independence="terrain area, not scan row; five areas in one Site04 DEM",
                    feature_caveat="No ground truth, condition, site, seed, mode, run ID or label is a model input. "
                                   "The six local-match features cannot uniquely distinguish global map registration error.",
                    no_model_parity_passed=True)
    artifacts = ("features.csv", "labels.csv", "groups.csv", "shadow_decisions.csv")
    manifest["artifact_sha256"] = {name: sha(output / name) for name in artifacts}
    manifest["reproduction_sha256"] = snapshot_sources(output)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "baseline_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    lines = ["# Scan trust data preparation (no training)", "",
             f"{counts['valid_examples']} valid scan proposals; {counts['bad_examples']} leave over 10 m error.",
             "Counts are correlated observations, not independent missions.", "",
             "| Slice | Accepted | Accepted with >10 m error | Rejected with <=10 m error |",
             "|---|---:|---:|---:|"]
    for key, a in audit.items():
        lines.append(f"| {key} | {a['accepted']} | {a['accepted_bad']} | {a['rejected_safe']} |")
    lines += ["", "Features, labels and group metadata are separate CSVs. Split by area, never by individual scan.",
              "No-model gate acceptance matches the geometric baseline on every archived scan.",
              "No learned model was evaluated and no new landing outcome was generated.",
              manifest["split_caveat"], manifest["feature_caveat"], ""]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(dict(output=str(output), **dict(counts), split_counts=dict(splits)), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "out/terrain_matching/20261021_183805_expanded_v2")
    parser.add_argument("--output", type=Path, default=ROOT / "out/scan_trust/20261022_preparation_v1")
    args = parser.parse_args()
    prepare(args.source, args.output)
