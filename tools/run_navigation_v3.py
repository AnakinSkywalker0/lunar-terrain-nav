"""Run navigation v3 in a separate Unity batch process, with checked exit/status.

The project must be closed in any other Unity Editor. Interactive users can use
the SensorTrust > Navigation v3 menu instead. Never use -quit for Play-mode jobs.
"""
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"contracts": "Verify", "smoke": "RunSmoke", "evaluation": "RunEvaluation", "build-demo": "BuildDemo", "visual": "Run"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=METHODS)
    parser.add_argument("--unity", type=Path, default=Path(os.environ.get("UNITY_EDITOR", r"D:\Unity\UnityEditors\6000.3.24f1\Editor\Unity.exe")))
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if not args.unity.is_file():
        raise FileNotFoundError("Set --unity or UNITY_EDITOR to the installed Unity 6000.3.24f1 executable")
    out = ROOT / "out/navigation_v3"
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    log = out / f"{timestamp}_{args.stage}.log"
    owner = "NavigationDemoVerification" if args.stage == "visual" else "NavigationExperiment"
    command = [str(args.unity), "-batchmode", "-projectPath", str(ROOT / "LANTERN"),
               "-executeMethod", f"SensorTrust.Editor.{owner}.{METHODS[args.stage]}", "-logFile", str(log)]
    if args.stage != "visual":
        command.append("-nographics")
    if args.stage == "build-demo":
        command.append("-quit")
    pointer = out / f"latest_{args.stage}.txt"
    previous = pointer.read_text() if pointer.exists() else None
    print(f"Unity {args.stage}; log: {log}", flush=True)
    subprocess.run(command, cwd=ROOT, timeout=args.timeout, check=True)
    if args.stage in ("smoke", "evaluation", "visual"):
        if not pointer.exists() or pointer.read_text() == previous:
            raise RuntimeError("Unity exited without publishing a new completed run; inspect its log")
    if args.stage in ("smoke", "evaluation"):
        folder = Path((out / f"latest_{args.stage}.txt").read_text().strip())
        status = json.loads((folder / "status.json").read_text())
        if status["state"] != "complete" or status["completed"] != status["expected"]:
            raise RuntimeError(f"Incomplete Unity job: {status}")
        print(folder)
    elif args.stage == "contracts":
        report = json.loads((out / "contracts.json").read_text())
        if not report["passed"]:
            raise RuntimeError(report)
        print(f"Passed {len(report['checks'])} contract groups")
    elif args.stage == "visual":
        folder = Path((out / "latest_visual.txt").read_text().strip())
        report = json.loads((folder / "verification.json").read_text())
        if not report["passed"]:
            raise RuntimeError(report)
        print(f"Live demo checks passed: {folder}")


if __name__ == "__main__":
    main()
