# LANTERN navigation v3 — implementation and verification record

**4 November 2026. Status: implemented engineering prototype; further Unity
execution paused at the user's request.** Final code-only changes listed below
have not been compiled or run in Unity. ML is disabled by default.

## What is now implemented

The live scene and batch runner use the same navigation/physics code:

```
Simulated IMU + time-stamped range + terrain scans
  -> position / velocity / bias prediction
  -> terrain geometry and innovation checks
  -> optional bounded ML down-weighting
  -> delayed-measurement replay and fused state
  -> approach guidance / terminal lateral braking / degraded mode
  -> forces, actual PhysX contact and recorded outcomes
```

- **Ten-state EKF:** 3-D position, velocity, accelerometer bias, and a local
  terrain-height bias. Joseph-form covariance updates retain cross-axis terms.
  The common map-height error is not treated as a fresh independent error for
  every altimeter reading. Range fusion includes the map-height gradient.
- **Measurement-time processing:** a bounded 1.5 s history replays the IMU and
  observations chronologically. Duplicate, expired, future and invalid readings
  are rejected. Historical terrain fixes remain fixed observations; replay does
  not rerun the terrain matcher. This is a local fixed-lag estimator, not a full
  nonlinear smoother.
- **Terrain-fix checks:** reuse the existing translation matcher, reject poor
  geometry, and approximate horizontal measurement covariance from centred
  terrain gradients and residuals. An effective-support cap addresses correlated
  samples approximately; this covariance is not empirically calibrated.
- **Guidance:** lateral velocity commands respect stopping-time/acceleration
  limits. A terminal braking phase latches near touchdown. Vertical descent
  settles toward 0.6 m/s in the last 3 m. Stale/unknown altitude triggers an
  explicit degraded mode. This is a fallback behaviour, not a safety guarantee.
- **Optional ML:** reuse the frozen v2 forest. Its utility prediction can inflate
  terrain measurement covariance by a factor of 1–4, after the classical
  innovation gate. It cannot rescue a rejected reading or issue thrust commands.
  Invalid/unavailable predictions fall back to conventional weighting. This is
  an experimental adaptation of an old utility model, not a newly trained or
  calibrated reliability estimator.
- **Live Unity controls:** pause/resume, restart, scenario selection, 1x/4x speed,
  and ML toggle on restart. Displays estimated altitude/velocity/uncertainty,
  measurement age, guidance mode, fuel and contact results. Overview markers are
  enlarged; an inset shows the lander model at its normal scale.

## Files

| File | Responsibility |
|---|---|
| `LANTERN/Assets/Scripts/Experiments/NavigationFilterV3.cs` | EKF, observation contracts, fixed-lag replay |
| `LANTERN/Assets/Scripts/Experiments/LandingGuidanceV3.cs` | Terrain covariance proxy, bounded ML influence, guidance and shared scoring |
| `LANTERN/Assets/Scripts/Experiments/NavigationSimulationV3.cs` | Isolated physics, sensor adapter, seeded faults and actual contact |
| `LANTERN/Assets/Scripts/Experiments/NavigationDemoV3.cs` | Live scene behaviour and controls |
| `LANTERN/Assets/Editor/NavigationExperimentV3.cs` | Menus, batch jobs, frozen artifacts and CSV logging |
| `LANTERN/Assets/Editor/NavigationV3Verification.cs` | Mathematical/behavioural contract checks |
| `LANTERN/Assets/Editor/NavigationDemoVerification.cs` | Live-scene, control and render checks |
| `tools/prepare_navigation_v3.py` | Reproducible terrain/error-proxy generation; refuses to overwrite inputs |
| `tools/run_navigation_v3.py` | Explicit Unity process invocation and completion checks |
| `tools/summarize_navigation_v3.py` | Offline verification, both-frame scoring and descriptive comparisons |

The earlier `TerrainNavigationCore.cs`, ML model and archived experiment runners
are retained. The v3 comparisons all use the new fusion system; `classical_pd`
is an ablation of the new guidance, not a replay of the entire old system.

## Inputs and assumptions

Four 2.4 km Site01 crops are stored under
`LANTERN/Assets/Experiments/NavigationV3/`. One is development terrain; three
were selected before evaluation and exclude the previous transfer crops.
Site01 itself was already exposed in earlier project work.

Ground uses 513 samples across the crop; the onboard prior uses 301. Both come
from the same NASA 5 m source raster. A synthetic, spatially smoothed random
field is multiplied by the local `toterr` values to perturb ground heights.
Generated RMS errors range from 0.36 to 0.43 m across these crops. The assumed
50 m smoothing scale is **not** a verified PGDA spatial covariance.
These are **not PGDA Monte Carlo clone DEMs or independent lunar ground truth**.

Fixed simulation settings, archived per run:

- Physics/IMU: 0.05 s step; range: 10 Hz with 0.15 s delivery delay; scan: every
  3 s with 0.30 s delivery delay, above an estimated 80 m scan envelope.
- Initial horizontal estimate error: 25–70 m with seeded direction; vertical
  estimate error: 2 m standard deviation; initial velocity error: 0.5 m/s per axis.
- Acceleration bias: 0.003 m/s² per-axis standard deviation; acceleration white
  noise: 0.01 m/s². Constant scan/acceleration attitude error: 0.02° standard deviation.
- Range noise: 0.1 m. Scan range noise: `0.05 + 0.001*range` metres; 2% ray dropout.
- Faults: +100 m range spike (12–18 s), range outage (12–22 s), scan outage
  (9–24 s), gross 22/-31 m map shift, gross +16 m relief change.

These are declared engineering settings, not a flight sensor specification.
The vehicle still has fixed rotation/ideal force response and 3-DOF translation.
Scans are instantaneous acquisitions with delayed delivery, not rolling scans.
There is no camera fusion, Doppler velocity sensor, dust model, 6-DOF lander,
hazard-site selection, or independent absolute map-registration observation.

## Existing execution evidence

The following jobs completed **before the user asked to stop Unity execution**:

1. First 18-case smoke (`20261104_041155_393_smoke`) with the initial nine-state
   implementation. It is retained as development evidence.
2. Revised 18-case smoke (`20261104_041543_046_smoke`) with persistent map-height
   bias and the revised vertical flare. Offline verification passed for all
   18 records and 10,121 sensor receipts.
3. Live demo checks, final capture folder `20261104_042147_760_visual`: default
   classical mode, pause, restart with ML, missing-model fallback, scenario
   switching, render output, and no runtime exceptions. Rendered previews do
   not include the IMGUI overlay; they check the terrain/markers/vehicle cameras.
4. Reserved evaluation `20261104_042217_834_evaluation`: 324 cases, 315,724
   sensor receipts, three observed crops. Thirteen contract groups passed in
   that source snapshot. Frozen hashes, pairing, timestamps, ML routing, sensor
   counts, trajectories and both-frame scores passed offline verification.

The reserved run had 318 contacts and six retained timeouts, all in the gross
map-shift condition. Do not describe all 324 cases as successful descents.
For non-contact rows, `impact_vz/impact_vh` contain termination velocity, not a
measured impact. Success always requires contact.

| Policy | Cases | Mean map-target distance at termination | 10 m map-target successes | 50 m map-target successes | Excess-speed contacts |
|---|---:|---:|---:|---:|---:|
| New fusion + PD | 108 | 30.79 m | 46 | 80 | 25 |
| New fusion + terminal guidance | 108 | 29.00 m | 45 | 83 | 21 |
| Same terminal system + frozen ML advice | 108 | 26.11 m | 37 | 87 | 17 |

Success also requires vertical speed <2 m/s and horizontal speed <1 m/s.
These pooled means include gross stress conditions and non-contact terminations;
inspect the per-condition and per-area tables before interpreting them.
In nominal conditions the classical terminal arm had 9/18 10 m successes and
17/18 50 m successes; the ML arm had 6/18 and 18/18 respectively. Thus neither
general robustness nor a consistent ML improvement is established.

Each arm rejected all 1,080 delivered injected range-spike readings at delivery.
Healthy-reading rejection also remains material (e.g. 2,509 of 15,957 nominal
range receipts in the classical terminal arm). These are delivery-time decisions;
fixed-lag replay can revise historical gates. This exposes a recovery/calibration
problem to diagnose, not a completed sensor-integrity solution.

Full results: [reserved report](../out/navigation_v3/20261104_042217_834_evaluation/analysis/REPORT.md),
[verification](../out/navigation_v3/20261104_042217_834_evaluation/analysis/verification.json),
[sensor decisions](../out/navigation_v3/20261104_042217_834_evaluation/analysis/range_decisions.csv).
Three crops support descriptive comparisons, not broad lunar-site confidence intervals.

## Code-only follow-up after Unity was paused

- Replay now stores its own copy of each observation so a caller cannot modify
  a past reading by reusing a packet. Added a fourteenth contract group.
- Live HUD now exposes runtime ML fallback counts and restart semantics.
- Batch wrapper rejects stale completion pointers instead of mistaking an older
  completed run for a newly completed run.
- Offline report includes pooled results as well as condition/area breakdowns.

**These final C# changes have not been compiled/run in Unity.** Earlier results
refer to their archived source snapshots, not to a claimed test of every current
line. After the pause, only offline analysis, Python tests and code/docs review ran.
`python -m unittest discover -s tests -v`: 19 tests passed. The repository-wide
whitespace check flags a pre-existing line in `out/runs/runs_summary.csv`; that
unrelated historical row was not edited.

## Running later, when authorized

Open `LANTERN/Assets/Scenes/NavigationV3.unity` and press Play. Rebuild the scene
if needed with **SensorTrust > Navigation v3 > Build and open live demo**.
The ML checkbox and scenario selection take effect on Restart.

With the project closed in other Unity editors:

```text
python tools/run_navigation_v3.py contracts
python tools/run_navigation_v3.py smoke
python tools/run_navigation_v3.py visual
```

The wrapper defaults to the verified installed Unity 6000.3.24f1 path; `--unity`
or `UNITY_EDITOR` can select another installation. Do not add `-quit` to
asynchronous Play-mode runs. Results go into a new timestamped folder.

Offline scoring needs no Unity:

```text
python tools/summarize_navigation_v3.py out/navigation_v3/20261104_042217_834_evaluation
```

Next authorized Unity check should compile the current code, run all 14 contract
groups, then smoke-test packet ownership and the fallback HUD. The previously
reserved areas are now observed development evidence; another run on them is
a regression check, not an untouched research evaluation. Diagnose healthy-range
rejection and estimator recovery before claiming a reliable solution or fitting
another model. Protocol: [NAVIGATION_V3_PROTOCOL.md](NAVIGATION_V3_PROTOCOL.md).
