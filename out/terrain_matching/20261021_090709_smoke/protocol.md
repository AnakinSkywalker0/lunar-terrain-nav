# Short-descent terrain matching: protocol v1

Written before running the new experiment, 2026-10-21. Exploratory engineering
evaluation on the previously used Site04 terrain, not a held-out benchmark.

Question: does applying a lidar-to-map horizontal position correction improve
localisation and target arrival during short descents?

Stationary scans: 500, 1000, 2000 m above local ground; seeds 11, 22, 33;
initial navigation offset (+60, +0, -40) metres. Three environments: aligned map,
truth-only 12 m Gaussian relief change, and onboard map sampled with (+40,-24) m
coordinate misregistration. Both terrain representations are separate assets.

Descent: same 3 altitudes, 3 environments, 3 seeds, with matching OFF/ON (54
runs = 27 pairs). Same initial state and seed within each pair. A common random
number schedule supplies noise even when matches are not applied. Trajectories
can diverge after different control decisions; identical measurements are not
expected once vehicle locations differ. Start velocity (0,-10,0) m/s; target
horizontal position (0,0). No training or parameter selection from test results.

Fixed configuration: 0.05 s PhysX steps, lunar acceleration 1.62 m/s², initial
mass 2000 kg, fuel 800 kg, thrust limit 6000 N, Isp 300 s, ideal instantaneous
attitude/gimbal response limited to 10 degrees. Locked attitude is a deliberate
3-DOF simplification. IMU observes acceleration with 0.002 m/s² Gaussian noise;
initial velocity is known. Nadir altimeter noise sigma 0.10 m. Laser 24x24 beams,
40-degree FOV, range noise sigma 0.05 + 0.001*range, 2% dropout. Scan every 3 s
above 80 m AGL. These are assumed sensor models, not flight calibration.

Both policies receive the same onboard map and direct altimeter. Horizontal
guidance consumes estimated position/velocity only. Vertical guidance consumes
measured altitude and estimated vertical velocity. Truth is restricted to the
physics/sensor adapter, initial-condition generation and evaluation. No truth
position is passed to the matcher or guidance law after initialization.

Matcher: mean-centred height residual over local lidar points; coarse search
±128 m at 16 m spacing, refinements at 4 m and 1 m. Acceptance requires at least
80 returns, RMS <= 8 m, contrast confidence >= 0.35, and an interior coarse
minimum. Contrast is a heuristic, NOT calibrated probability. No fine-tuning
after seeing outcomes. A confidently accepted correction whose horizontal
error exceeds 10 m counts as a wrong match. Count failures and rejections too.

Metrics: stationary before/after horizontal error; match residual, confidence,
latency and wrong matches. Descent horizontal/vertical navigation error, target
miss, impact vertical/horizontal speed, remaining fuel, match acceptance and
wrong-match count. Geometric touchdown requires contact proximity. Task success
requires touchdown, vertical speed <2 m/s, horizontal speed <1 m/s and target
miss <10 m. Report individual conditions and paired differences, not just pooled
success. Timeout 360 simulated seconds. Store every scan and 1 Hz trajectories.

First smoke checks are implementation checks; full v1 results are kept separately
from any later revisions. Save source hashes and configuration with outputs.
The map-shift case intentionally tests a limitation: a shape match may be
confident but wrong in the absolute coordinate frame.
