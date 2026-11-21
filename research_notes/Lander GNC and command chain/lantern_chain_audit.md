# LANTERN simulated lander chain vs a real lander's GNC and command/authority chain

Audit date: 29 October 2026. Workspace `D:\newprj` is read-only; only this note was written, and nothing was executed. This note builds on `research_notes/Lunar TRN literature verification/lantern_methodology_audit.md` (the "methodology audit"). That audit already covers matcher internals, the lidar pattern and noise, perturbation magnitudes, statistics and literature analogues for the learned gain. Those points are referenced here, not repeated. This note covers the whole chain: timing, estimation structure, guidance and actuator models, phases and modes, touchdown and cutoff, fault handling, and decision authority.

Evidence labels:
- **REPO**: read directly in the working tree (`path:line`).
- **COMPUTED**: my own arithmetic from repo constants, not a measured result.
- **PRIOR-AUDIT**: verified in the methodology audit; source and label are carried over from it.
- **SNIPPET**: search-engine summary only; the source was not opened. Two fetch attempts failed (404 / certificate error), and web search then hit its session limit.
- **GENERIC**: the user-supplied generic real-lander baseline (IMU 100–400 Hz, EKF ~1–10 Hz, guidance ~1–2 Hz, and so on). I did not verify it independently here, so treat it as an assumption.

Line-number note: several files were read as concatenations and re-based. All numbers below are file-relative.

---

## 1. What does each LANTERN execution path implement, stage by stage?

### Takeaway
LANTERN has **three distinct chains**, and they differ more than the docs suggest:
- **(A) Unity estimated-state short-descent experiments.** A 3-DOF point mass at 20 Hz, a near-perfect kinematic "IMU", a hard-reset position estimator, a PD position-tracking guidance law that commands a world-frame force vector directly, and episodes that end at first contact.
- **(B) Unity full-height Site04 demo.** A genuine 6-DOF rigid body with legs, body-fixed thrust and an attitude PD loop at 50 Hz. It flies on **true** state, and LUMEN runs **open-loop**: its fix is displayed and logged, never used.
- **(C) Python bench.** A batched 3-DOF point mass at a single 4 Hz rate with a real 9-state EKF (position, velocity, accelerometer bias), altimeter and camera fault handling, and guidance that *does* null horizontal velocity below 60 m.

### Cited Findings

#### (A) Unity estimated-state short-descent experiments (`ShortDescentExperiment.cs`, `ScanTrustExperiment.cs`, `ScanUtilityRunner.cs`, `ScanUtilityTransferRunner.cs`, `TerrainNavigationCore.cs`)

**Truth dynamics and integration**
- A Rigidbody in an isolated PhysX scene, with rotation frozen (`RigidbodyConstraints.FreezeRotation`), mass reset to 1200 + fuel each step, gravity applied manually as a force, and a 0.4 m sphere collider — REPO `LANTERN/Assets/Editor/ShortDescentExperiment.cs:226-230,317-318`; identical in `ScanUtilityRunner.cs:251-255,361-362`.
- Fixed step Dt = 0.05 s (20 Hz). Physics is advanced manually with `physics.Simulate(Dt)` from an `EditorApplication.update` loop, in ≤35 ms wall-clock batches. Simulated time is therefore decoupled from wall time — REPO `ShortDescentExperiment.cs:15,285-294,320`.
- Initial state: vertical velocity −10 m/s, zero horizontal velocity, altitudes 500/1000/2000 m (v1) or 500/1500 m (utility evaluation). In utility runs the true start is offset from the target by (−12, +16) m — REPO `ShortDescentExperiment.cs:231-232`; `ScanUtilityRunner.cs:145,152,256-257`.

**Sensors (simulated from truth)**
- *"IMU"*: acceleration = (v_k − v_{k−1})/Dt of the true PhysX velocity, plus white noise σ = 0.002 m/s² per axis per step — REPO `ShortDescentExperiment.cs:300-301`. This is a **kinematic-acceleration oracle that includes gravity**. A real accelerometer measures specific force in the body frame, which requires attitude knowledge and a gravity model. There is no bias, scale factor, misalignment, attitude or gyro. (Gyros are moot because rotation is frozen.)
- *Altimeter*: a nadir raycast from the true position, σ = 0.1 m, every step (20 Hz). No faults, delay, footprint or slant geometry — REPO `ShortDescentExperiment.cs:303-305`.
- *Lidar scan*: 24×24 rays, instantaneous, cast from the true position with perfect attitude. Details are in the methodology audit (PRIOR-AUDIT) — REPO `ShortDescentExperiment.cs:246-257`.
- *Velocity sensor*: none. Velocity knowledge comes only from IMU integration starting at the true initial velocity — REPO `ShortDescentExperiment.cs:233`.

**Timing and rates (REPO; COMPUTED where noted)**
- Run at 20 Hz: truth physics, IMU propagation, altimeter update, guidance command — `ShortDescentExperiment.cs:295-320`.
- Run at 1/3 Hz: lidar scan + match, on a fixed clock (`nextScan += 3`) and only when measured AGL > 80 m. Below 80 m the scan is still drawn, to keep random streams aligned across arms, but not matched — `ShortDescentExperiment.cs:307-312`.
- Scan acquisition, matching and correction all complete **within the same 0.05 s step**: zero processing latency and no motion during the scan. The matcher's wall time is measured (`milliseconds`) but never simulated as latency — `TerrainNavigationCore.cs:52,81`; `ShortDescentExperiment.cs:258-273`.

**Navigation estimate**
- `NavigationEstimate` holds only a position and a velocity vector: no covariance and no bias state — REPO `TerrainNavigationCore.cs:86-91`.
- Predict: position += v·dt + ½a·dt², velocity += a·dt, run every step after t = 0 — `TerrainNavigationCore.cs:90-91`; `ShortDescentExperiment.cs:302`.
- Vertical channel: every step, the estimated height is **overwritten** as map(est x, z) + measured range — `TerrainNavigationCore.cs:92-93`.
- Horizontal channel: an accepted scan **adds** its correction (×gain in utility runs) to position. Velocity is never corrected — `TerrainNavigationCore.cs:94-95`; `ScanUtilityRunner.cs:305-306`.
- COMPUTED: the velocity estimate's random walk is σ ≈ 0.002 × 0.05 = 1×10⁻⁴ m/s per step, so ≈ 0.0085 m/s after the 360 s timeout (7200 steps). Velocity is effectively perfect against the 1 m/s touchdown threshold.

**Measurement acceptance ("trust") logic**
1. Geometric gate inside the matcher: not on the coarse boundary, RMS ≤ 8 m, confidence ≥ 0.35 — REPO `TerrainNavigationCore.cs:64,80` (PRIOR-AUDIT details).
2. Arm-specific gate:
   - v1/expanded: ON applies every geometrically accepted scan, OFF none — `ShortDescentExperiment.cs:271-272`.
   - Scan-trust v1: `geometric` / `rule` / `ml` veto. The ML and rule gates both require `m.accepted` first — `ScanTrustExperiment.cs:260-265`; `LANTERN/Assets/Scripts/Experiments/PortableScanTrust.cs:89-92`.
   - Utility v2: a gain g ∈ [0,1] from `ScanUtilityPolicy.Gain`. It is 0 if the scan was not valid or not accepted, and 0 if the model prediction is non-finite (except for `bounded`). `bounded` and `utility_hybrid` clamp |g·d| ≤ max(5 m, 0.5·AGL) — `ScanUtilityPolicy.cs:57-69`; applied at `ScanUtilityRunner.cs:299-306` and `ScanUtilityTransferRunner.cs:316`.
3. No covariance gating, innovation test against an IMU-propagated prediction, multi-scan voting, or rate limit, apart from the clamp above. The only history is the utility "consistency" feature, i.e. the distance between this correction and the unapplied residual of the previous one — `ScanUtilityRunner.cs:299,315`.

**Guidance**
- `EstimateGuidance.Thrust` runs every step on the estimate and the measured AGL — REPO `TerrainNavigationCore.cs:101-109`.
  - Vertical: v_des = −min(30, 0.5 + √(0.9·(AGL−0.5))); a_y = max(0, 1.62 + 0.8·(v_des − v̂_y)).
  - Horizontal: a_h = −0.04·x̂ − 0.5·v̂, clamped to |a_h| ≤ a_y·tan 10°.
- The force vector is (a_h, a_y)·mass, clamped to |F| ≤ 6000 N.
- The target is the fixed origin of the estimate frame. There is no retargeting, no hover, and no phase in which position control is dropped.
- COMPUTED:
  - The vertical loop's time constant is 1.25 s.
  - The profile implies a constant 0.45 m/s² net deceleration.
  - Full-tank T/W = 6000/(2000·1.62) ≈ 1.85.
  - Near hover, lateral authority is ≈ 1.62·tan 10° ≈ 0.29 m/s².
  - Time from the last scan (80 m) to contact on the profile ≈ 2√80/√0.9 ≈ 19 s, consistent with PRIOR-AUDIT.

**Control / attitude and actuator**
- There is no attitude: rotation is frozen and the guidance force is applied in the world frame with `AddForce`. The "10° tilt" is only a clamp on the lateral/vertical ratio, so thrust vectoring is instantaneous and free — REPO `ShortDescentExperiment.cs:228,318`; `TerrainNavigationCore.cs:107`.
- No throttle lag, rate limit, minimum throttle, thrust misalignment, thrust-magnitude error, RCS, or engine start/stop transient. Commanded force equals the applied force in the same step — `ShortDescentExperiment.cs:315-320`.

**Mass and fuel**
- fuel −= |F|/(Isp·g₀)·Dt with Isp 300 s, 800 kg initial, dry mass 1200 kg; mass updated each step; thrust = 0 when fuel = 0 — REPO `ShortDescentExperiment.cs:234,315-319`. No centre-of-mass or inertia effects (rotation frozen).

**Touchdown detection and engine cutoff**
- Expanded/scan-trust/utility/transfer: first PhysX contact with the `TerrainCollider`, recorded by `TerrainTouchdownRecorder`, using `collision.relativeVelocity`. The recorder is flagged as "Never read by navigation or guidance" — REPO `LANTERN/Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs:5-16`; `ShortDescentExperiment.cs:322-323`; `ScanUtilityRunner.cs:99,366-367`.
- v1: geometric proximity gap < 0.08 m while descending — `ShortDescentExperiment.cs:324-325`.
- The episode **terminates** at contact (`Complete` → `Next`). There is no engine-cutoff logic, no post-contact dynamics (bounce, tip-over, slope/leg loads), and no check of touchdown attitude or slope — `ShortDescentExperiment.cs:329-334`.
- Success = touchdown ∧ v_z < 2 ∧ v_h < 1 ∧ miss < 10 m, with miss measured from the true-frame origin — `ShortDescentExperiment.cs:331-332`; `ScanUtilityRunner.cs:375-376`.

**Mode / phase management**
- The only phase-like switch is "scan matching on/off at measured AGL 80 m" — REPO `ShortDescentExperiment.cs:310`. "Stationary" cases are an offline single-scan test kind, not a flight mode — `:297-298`.
- Timeout at 360 s and |x| or |z| > 1000 m are evaluation terminations, not aborts — `:326-327`.

**Fault handling**
- None at the system level. There are no sensor faults to handle: the altimeter is always valid, and the lidar has only 2 % dropout. Matcher rejection is the only "fault" response. An exception inside a run stops the whole batch (`Finish("ERROR")`), which is a harness behaviour, not FDIR — REPO `ShortDescentExperiment.cs:288-293`.

#### (B) Unity full-height Site04 demo (`DescentAutopilot.cs`, `LanderController.cs`, `Lumen/*.cs`, `Site04SceneBuilder.cs`)
- *Vehicle*: a cylinder body plus four capsule legs, Rigidbody with continuous collision detection and centre of mass at 1.8 m, gravity −1.62 m/s². The lander is dropped from rest 102.5 km above the site — REPO `LANTERN/Assets/Editor/Site04SceneBuilder.cs:73,96,103-130`.
- *Physics rate*: Unity fixed timestep = 2822399/141120000 s = 0.02 s (50 Hz) — REPO `LANTERN/ProjectSettings/TimeManager.asset:7-11`. Time warp up to 8× above 8 km AGL, blended to 1× below 4 km, with the physics step unchanged — `LANTERN/Assets/Scripts/DescentAutopilot.cs:21-23,65-66`.
- *Engine*: body-fixed thrust `AddRelativeForce(up·throttle·6000 N)`, fuel burn from Isp 300 s, mass updated, throttle forced to 0 at zero fuel — REPO `LANTERN/Assets/Scripts/LanderController.cs:11-12,41-51`.
  - `throttleRate = 0.5 /s` applies **only to manual keyboard input**. The autopilot sets throttle instantly through `Command()`, so automatic flight has no throttle lag — `LanderController.cs:14,31-39,63-67`.
- *Attitude*: a PD torque law with ω_n = 2 rad/s and critical damping, inertia approximated as |I|/√3, yaw rate damped only, torque clamped to 4000 N·m and applied as body torque. This is an idealised reaction-torque actuator with no RCS pulse/thruster model — REPO `DescentAutopilot.cs:18,88-97`; `LanderController.cs:13`.
- *Guidance*:
  - The vertical profile is v_des = −(0.5 + √(2·a_net·h)), with a_net = 0.5·(T_max/m − g), and a_cmd = g + 4·(v_des − v_y).
  - The vehicle free-falls until v_y < v_des (it brakes only once it is faster than the profile). Throttle = a_cmd·m/(T_max·cos tilt).
  - Horizontal: tilt toward −0.05·v_h, ≤ 10°.
  - There is **no position target**: it nulls drift wherever it is — REPO `DescentAutopilot.cs:70-86`.
- *Navigation*: none. The autopilot reads **true** velocity (`rb.linearVelocity`) and **true** AGL from `terrain.SampleHeight` at the true position — REPO `DescentAutopilot.cs:53-57`. The project acknowledges that the demo "uses true-state autopilot information" — REPO `docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:86-87,107-109`.
- *LUMEN*: runs at 2 Hz below 2500 m true AGL. It uses a 64×64-beam, 40° scanner that takes **true attitude** from the transform. Its points are offset by a **constant injected error** (60, 0, −40) m, which is never corrected. The patch is matched with a ±16-cell search — REPO `LANTERN/Assets/Scripts/Lumen/LumenModule.cs:13-14,24,36-45,47-66`; `Lumen/LidarScanner.cs:12-17,63-65`; `Lumen/PatchMatcher.cs:21,55-81`.
  - The only consumers of `lumen.Last` are the HUD, the telemetry logger (which scores shift error against the injected truth) and an editor self-test. **No code path feeds LUMEN to the autopilot** — REPO `LanderHud.cs:27-28`; `TelemetryLogger.cs:53-61`; `Site04SceneBuilder.cs:140-141` (grep over `Assets/Scripts` and `Assets/Editor`).
  - `PatchMatcher` has no accept/reject gate: it sets `valid` only — `PatchMatcher.cs:77-81`.
- *Touchdown and cutoff*: `OnCollisionEnter` on any collider (legs included) sets `TouchedDown` and records the impact from the previous step's velocity. Afterwards the autopilot commands throttle 0 and zero torque. This is a **contact-triggered engine cutoff with zero delay**, and the only cutoff logic anywhere in LANTERN — REPO `DescentAutopilot.cs:68,102-110`.
- *Recorded outcome*: one touchdown row reports 583 s, 0.503 m/s vertical, 0 m/s horizontal, 250.8 kg fuel, LUMEN valid fraction 0.093, first fix at 2463 m AGL, max shift error 48.7 m. A second row is an immediate stop — REPO `out/runs/runs_summary.csv:2-3`. That row also reports `start_agl_m = 0` for a run that descended at up to 315 m/s, which I cannot explain from the logger code (`TelemetryLogger.cs:52`). Treat that field as unreliable.

#### (C) Python bench (`sim/engine.py`, `sim/pipeline.py`, `sim/world.py`, `sim/scan_trust.py`)
- *Rates*: a single DT = 0.25 s (4 Hz) for truth, IMU, EKF predict, altimeter update and guidance. The camera fix runs every 8 steps (0.5 Hz) below 12 km true AGL. The scan fix runs every 2 steps (2 Hz) at 80–2500 m true AGL, only for `*_scan` judges — REPO `sim/engine.py:12,207-208,499-500,543-545`.
- *Truth dynamics*: a point mass driven by the commanded acceleration vector, integrated with exact constant-acceleration kinematics. Fuel burn = m·|a_cmd|/(Isp·g₀)·DT; a_cmd = 0 at zero fuel — REPO `engine.py:280-293`. No attitude, throttle lag, minimum throttle or thrust error.
- *Start*: 15 km AGL, about 10 km from the target, v_h = 100 m/s toward the target, v_z = −140 m/s — REPO `engine.py:179-182`; `sim/world.py:206-239`.
- *IMU*: a_meas = a_cmd + bias + 0.003·N(0,1), with bias σ = 0.002 m/s² per axis. The IMU measures the *commanded* non-gravitational acceleration, and gravity is added in the filter — REPO `engine.py:89,130,314`. COMPUTED/inference: because the actuator is perfect, commanded equals actual acceleration, so there is no thrust-execution error for the navigation filter to absorb.
- *Navigation*: a batched 9-state EKF (p, v, b_a) with constant F, Q from σ_a = 0.003, and P₀ = diag(σ_pos², σ_pos², 30², 0.3²·3, 0.004²·3). Updates are sequential scalar updates — REPO `engine.py:98-134`. Initial errors are drawn: position σ = init_pos_sigma (default 100 m) horizontally and 30 m vertically; velocity σ = 0.3 m/s — `engine.py:87-88,187`.
- *Altimeter*: true AGL under the true position (no slant/footprint), σ = 1 + 0.0015·r. Fault bursts of ±30–400 m bias last 8–20 samples (2–5 s) at a scenario rate. Scenarios can add noise multipliers below an AGL, dropout below an AGL, or a 1–3 s delay. The measurement model is H = [−∂h/∂x, −∂h/∂y, 1] using the onboard-map gradient — REPO `engine.py:26-49,77-94,319-355`.
- *Camera*: a position fix built as truth + map registration shift + an empirical error drawn from the Unity camera survey, scaled by AGL. It is gated by matcher peak ≥ 0.5 and optionally by Sun-geometry lit fraction, and applied as per-axis scalar updates — REPO `engine.py:499-541`.
- *Scan*: a **synthetic** fix (truth + shift + Gaussian σ = max(4, 0.8·cell)), not the Unity matcher. It is accepted only if |fix − estimate| < 4σ + 50 m and roughness > 1.5 m — REPO `engine.py:543-557`.
- *Maps*: truth = DEM + unmapped craters/roughness. The onboard map is one of 4 banks of DEM + a correlated error field (σ = map_sigma, default 3 m, 150 m correlation length), with a per-run horizontal registration shift σ = 10 m/axis. "wrong" adds +2 km; "missing" uses a 4 km-smoothed coarse reference — REPO `sim/world.py:147-187`; `engine.py:90,215-232`.
- *Guidance* (on the EKF estimate) — REPO `engine.py:246-282`:
  - Horizontal: v_des = min(110, √(2·1·dist)) toward the target, **set to 0 below 60 m estimated AGL**; a_h = 0.5·(v_des − v̂_h), clipped to 1.5 m/s².
  - Vertical: v_des = −(0.7 + √(2·a_net·max(h_eff − 15, 0))), with glide-slope cone h_eff = AGL − 0.08·dist and a constant 0.7 m/s over the last 15 m.
  - Horizontal command is limited by the thrust remaining after the vertical demand.
- *Touchdown*: contact when the true z ≤ truth height. Success = v_z ≤ 2 ∧ v_h ≤ 1.5 ∧ slope ≤ 10° ∧ fuel > 0. Outcomes are landed / crash (v_z > 2) / rough / timeout at 800 s. Miss is measured to the target or the divert target. There is no engine-cutoff logic; the run simply ends — REPO `engine.py:294-310,572-576`.
- *Phases (implicit)*: camera below 12 km; scan at 80–2500 m; a one-shot divert retarget at estimated AGL < 5 km (`divert` scenario only); horizontal-velocity nulling below 60 m; constant-rate descent below about 15 m; and, in v2 with no map, an α-β terrain-relative altitude filter used for guidance below 200 m — REPO `engine.py:255-262,267,276,283-286,500,545`.
- *Fault handling / measurement judges*: altimeter readings go through one of `fixed`, `pitfal`, `tolerance`, `wait`, `second`, `ml`, `trust*`, `trust2*`, detailed in Q3 — REPO `engine.py:362-489`. ML classifier: RandomForest (120 trees, depth 14), trained on procedural worlds — `sim/pipeline.py:106-131`.
- *Python scan gate* (`scan_trust.py`): an inference-only learned veto applied after the geometric gate. It "cannot promote a geometrically rejected scan", fails closed on invalid features or inference errors, and validates the schema at load. Its docstring says it is "not a live Unity controller" — REPO `sim/scan_trust.py:1-5,26-72`.

### Inferences
- The three chains do not form one pipeline. The Unity experiments, which carry the TRN-gating conclusions, use the *least* realistic GNC: no filter, no attitude, a world-frame force actuator, and no terminal phase. The Python bench, which carries the altimeter-trust conclusions, has a real EKF and a terminal phase but a 4 Hz single-rate loop and a perfect actuator. The 6-DOF demo has the most realistic vehicle but no navigation in the loop. No single run combines a realistic vehicle with estimated-state closed-loop TRN.
- Unity's "IMU" includes gravity and has no attitude, so the experiments test position-fix gating on top of an essentially perfect dead-reckoner whose initial position offset is constant.

### Gaps
- I did not run anything. Rates and behaviours come from reading the code, not from logs.
- The `start_agl_m = 0` anomaly in `out/runs/runs_summary.csv:2` is unexplained.

---

## 2. Which real-lander stages are missing or idealised? (stage-by-stage table)

### Takeaway
LANTERN idealises nearly every stage outside the measurement-acceptance step itself. The most consequential gaps are:
- (i) no terminal velocity-nulling/vertical-descent phase in the Unity experiments, where the speed-violation results come from;
- (ii) perfect velocity and attitude in Unity;
- (iii) no actuator dynamics in any estimated-state path;
- (iv) no mode manager, abort or safe-fallback logic;
- (v) touchdown is defined as first collision, with no cutoff modelling.

The Python bench has the realistic estimator structure (EKF, χ² gating, bias state) that Unity lacks.

### Cited Findings

Real-lander reference anchors (beyond GENERIC):
- Apollo LM descent guidance used programs P63 (braking) and P64 (approach), then P66, which "begins automatically at typically 30-m altitude" (or by commander selection), controls velocity only with no position control, and was used for the actual landings — SNIPPET of Klumpp, *Apollo Lunar-Descent Guidance*, Draper R-695 (1971) ([ibiblio copy](https://www.ibiblio.org/apollo/Documents/Apollo%20Lunar%20Descent%20Guidance.pdf); [NASA ALSJ copy](https://www.nasa.gov/wp-content/uploads/static/history/alsj/ApolloDescentGuidnce.pdf) returned 404). A powered-flight attitude-maneuver routine linked all guidance programs to the digital autopilot (same SNIPPET).
- Chang'e-3: autonomous ~12 min powered descent from ~15 km; a 1,500–7,500 N variable-thrust engine; a hover at ~100 m for hazard assessment; descent to ~3 m, then engine shutdown and free fall onto shock-absorbing legs — SNIPPET (news-level, [Universe Today](https://www.universetoday.com/articles/china-scores-historic-success-as-chang-3-probe-lands-on-the-moon-today), [GlobalSecurity](https://www.globalsecurity.org/space/world/china/change-3.htm)). Sources disagree slightly on details.
- ALHAT ALDAC-2: 6-DOF POST2 Monte Carlo dispersing thrust, Isp, mass properties, sensors and navigated initial state; TRN from 15 to 5 km; velocimeter from 2 km; vertical descent from ~30 m; altimeter and velocimeter deactivated during HRN — PRIOR-AUDIT, VERIFIED-FULLTEXT ([NTRS 20100025998](https://ntrs.nasa.gov/api/citations/20100025998/downloads/20100025998.pdf)).
- Linear-covariance analysis models navigation state *and covariance* resets and post-divert replanning as explicit events — PRIOR-AUDIT, VERIFIED-FULLTEXT ([Woffinden, NTRS 20210026438](https://ntrs.nasa.gov/api/citations/20210026438/downloads/EvalLunarDescentResetting.pdf)).

#### Stage-by-stage table

| Real-lander stage | Typical real implementation (GENERIC unless cited) | LANTERN Unity (A: experiments; B: Site04 demo) | LANTERN Python bench (C) | Gap and effect on validity of LANTERN conclusions |
|---|---|---|---|---|
| Inertial sensing | IMU 100–400 Hz; specific force + angular rate; bias, scale factor, misalignment; attitude needed to rotate into the nav frame | **A**: 20 Hz finite difference of true velocity, *includes gravity*, σ 0.002 m/s², no bias, no gyro (`ShortDescentExperiment.cs:300-301`). **B**: none (truth used) | 4 Hz; a_cmd + bias(σ 0.002) + noise 0.003; gravity added in filter (`engine.py:89,130,314`) | Unity velocity is effectively perfect (COMPUTED ≤ 0.01 m/s). Initial position error stays a constant offset, so rejecting a scan costs nothing in drift. That flatters conservative/reject policies, and touchdown v_h can only come from guidance. Python is closer, but its IMU sees the commanded acceleration, so actuator errors are invisible |
| Velocity sensing | Doppler radar/lidar velocimeter in the terminal phases (ALHAT: from 2 km, PRIOR-AUDIT) | None; true initial velocity (`ShortDescentExperiment.cs:233`) | None; velocity observable only through EKF position/altimeter updates; v₀ error σ 0.3 m/s (`engine.py:88`) | Unity makes velocity errors impossible, so the v_h failures are not navigation failures. A real velocimeter would also let a terminal phase null v_h independently of TRN |
| Altimetry | Radar/laser altimeter, slant beams, multi-beam; faults, dropouts, delay | **A**: nadir truth raycast, σ 0.1 m, 20 Hz, no faults (`:303-305`). **B**: true AGL (`DescentAutopilot.cs:57`) | Nadir truth AGL, σ 1 + 0.0015r, bursts ±30–400 m, noise/dropout/delay scenarios (`engine.py:319-335`) | Unity's vertical channel is near-ideal, so vertical-speed outcomes are near-guaranteed. Python models altimeter faults richly, but single-beam only (no slant/multi-beam voting) |
| TRN / lidar sensing | Flash/scanning lidar or camera; finite acquisition time; latency of 0.1–several s; pointing/lever-arm errors | **A**: 24×24 instantaneous rays from the true pose, matched in the same step, every 3 s above 80 m (`:246-257,307-311`). **B**: 64×64, 2 Hz below 2.5 km, true attitude, open-loop (`LumenModule.cs:13-14,47-66`) | Synthetic Gaussian scan fix at 2 Hz (`engine.py:543-557`); empirical camera fix at 0.5 Hz (`:499-541`) | Zero latency and no attitude coupling make Unity fixes optimistic. COMPUTED: a 1° attitude error at 500 m AGL shifts points ≈ 8.7 m, comparable to the 10 m miss criterion, so it could break the "aligned ≈ 100 %" result. Python's scan is not the real matcher, so Python scan results say nothing about matcher behaviour |
| Navigation filter | EKF/UKF/PMF at ~1–10 Hz with covariance, bias states, measurement gating; resets of state *and* covariance (Woffinden, PRIOR-AUDIT) | **A**: deterministic position/velocity propagator; vertical overwrite every step; additive horizontal reset; no covariance (`TerrainNavigationCore.cs:86-96`). **B**: none | 9-state EKF (p, v, b_a), sequential scalar updates, χ² gating (`engine.py:98-134,352-367`) | Unity cannot express "how much to trust" except through an ad-hoc gain; the learned g is a stand-in for K = P/(P+R) (PRIOR-AUDIT). Unity conclusions about gating are therefore conclusions about a filterless reset loop, not about TRN in an EKF |
| Measurement acceptance / trust | χ² innovation gating, multi-sensor consistency, residual-based FDI, adaptive R | **A**: geometric gate (RMS, confidence, boundary) → arm gate/gain (`TerrainNavigationCore.cs:80`; `ScanUtilityPolicy.cs:57-69`; `PortableScanTrust.cs:89-92`) | χ² gate; R inflation after a flag; terrain/map tolerance; physical-possibility bounds; K-sample probation; IMU/camera second opinion; RF fault classifier; adaptive noise s_hat; time-stamp delay compensation; cautious mode (`engine.py:362-489`) | Python's acceptance logic is much closer to real practice. Unity's has no innovation test against a propagated prediction, which a real filter would use to reject a gross wrong match |
| Guidance | Polynomial/E-guidance (Apollo P63/P64 quadratic-acceleration targeting, SNIPPET), ~1–2 Hz; retargeting; time-to-go aware | **A**: 20 Hz PD to origin, −0.04x̂ − 0.5v̂, tilt-ratio clamp, sqrt vertical profile; no time-to-go and no terminal freeze (`TerrainNavigationCore.cs:101-109`). **B**: sqrt profile, free-fall-then-brake, v_h nulling, no position target (`DescentAutopilot.cs:70-86`) | 4 Hz velocity-to-target law, glide cone, **v_h → 0 below 60 m**, 0.7 m/s final 15 m, optional one-shot divert (`engine.py:246-282`) | Unity's continuous position tracking to 0 m AGL turns every late position correction into touchdown lateral velocity. This is the main validity threat to the Unity speed-violation results (Q4). Python's law has the terminal nulling Unity lacks |
| Terminal descent phase | Velocity-only vertical descent from ~30 m (Apollo P66, SNIPPET; ALHAT ~30 m, PRIOR-AUDIT); hover/hazard-check (Chang'e-3 ~100 m, SNIPPET) | **A**: absent. **B**: effectively velocity-only (no position target at all) | Present (60 m v_h nulling; 15 m constant-rate) | Absent where the TRN-gating results are produced |
| Attitude control | Attitude loop ~10–50 Hz; RCS or gimbal; thrust direction follows attitude with lag | **A**: none; rotation frozen; world-frame force (`ShortDescentExperiment.cs:228,318`). **B**: PD ω_n 2 rad/s, ideal torque ≤ 4000 N·m (`DescentAutopilot.cs:88-97`) | None; acceleration vector applied directly (`engine.py:280-293`) | In A and C lateral acceleration is available instantly, so real tilt-up lag (seconds) is missing. Inference: that would *worsen* correction-induced lateral transients and lengthen nulling |
| Throttle / engine dynamics | Throttle range limits (e.g. Chang'e-3 1.5–7.5 kN, SNIPPET), first-order lag, rate limits, minimum-throttle band, start/stop transients | **A**: instant 0–6000 N, any direction. **B**: instant throttle under autopilot; 0.5/s rate only for manual (`LanderController.cs:14,31-39,63-67`) | Instant 0–T_max | No lag or minimum throttle anywhere. Inference: optimistic for both vertical-speed and lateral outcomes; fuel numbers are idealised |
| Mass / fuel | Mass depletion, CoM shift, slosh, propellant reserve / bingo-fuel logic | Rocket equation from Isp, mass update; thrust 0 at empty (`ShortDescentExperiment.cs:315-319`; `LanderController.cs:41-51`) | Same (`engine.py:288-290`); success requires fuel > 0 | Adequate for relative comparisons; no reserve logic, slosh or CoM effects |
| Mode / phase manager | Explicit mode sequencer with entry/exit criteria (braking → approach → terminal → touchdown); sensor-enable schedules | **A**: only "match if AGL > 80 m" (`:310`). **B**: free-fall/brake switch; time warp (`DescentAutopilot.cs:65-66,86`) | Inline altitude conditionals (camera < 12 km; scan 80–2500 m; divert < 5 km; nulling < 60 m; α-β < 200 m) (`engine.py:255-286,500,545`) | No explicit manager in any path. The effect is mainly on what can be tested: freezing TRN updates before the terminal phase, or a hover-and-reassess phase, cannot be evaluated today |
| FDIR / fallback / abort | Sensor voting/redundancy, health monitoring, safe fallback (e.g. inertial-only, hover, retarget), abort-to-orbit | **A**: none beyond matcher rejection; run exception ends the batch (`ShortDescentExperiment.cs:288-293`). **B**: none | Altimeter FDI judges and cautious mode; coarse-reference/no-map fallback; no voting across redundant units; no abort (`engine.py:362-489`; `world.py:184-187`) | No path can choose "abort" or "hold". Every run must touch down or time out, so outcomes measure navigation quality *without* the safety net real landers use |
| Touchdown sensing / engine cutoff | Contact probes / touchdown sensors → engine cutoff; or cutoff at a few metres and free fall (Chang'e-3 ~3 m, SNIPPET) | **A**: first PhysX contact (or 0.08 m gap in v1) ends the episode; no cutoff (`TerrainTouchdownRecorder.cs:11-16`; `ShortDescentExperiment.cs:321-325`). **B**: any-collider contact → throttle 0 instantly (`DescentAutopilot.cs:68,102-110`) | z ≤ terrain ends the run; slope ≤ 10° checked (`engine.py:294-310`) | Powered contact at ~0.5 m/s is assumed. COMPUTED: cutting off at 3 m adds √(2·1.62·3) ≈ 3.1 m/s, which alone would fail the v_z < 2 criterion. The criteria are not comparable to a cutoff-above-surface lander |
| Ground-in-the-loop / authority | Ground uplinks state vectors, landing-site maps, go/no-go; crew or autonomy may redesignate/abort | None; all decisions onboard and fixed before launch | None | No uplink, no human override (except manual keys in the demo), no go/no-go. Fine for an autonomy study, but no "chain of command" result can be claimed |
| Hazard detection & avoidance | HDA scan near terminal phase; divert; reset (Woffinden, PRIOR-AUDIT) | None | One-shot scripted divert to a flat spot about 2 km away (`engine.py:259-262,588-603`) | Not evaluated in Unity |

### Inferences
- The gaps all lean the same way for the *aligned* cases: perfect velocity, perfect attitude, instantaneous scans, ideal actuators and an ideal altimeter all make success easier. The aligned ≈ 100 % results are an upper bound.
- For the *speed-violation* results, the gaps pull in opposite directions. Missing actuator lag and instant lateral authority are optimistic. The missing terminal phase is pessimistic, and it probably dominates (Q4).

### Gaps
- Exact real-lander rates (IMU, nav, guidance, attitude loop) are GENERIC, not verified here. Apollo and Chang'e-3 details are SNIPPET-level: web search hit its session limit before I could open the Klumpp report or find a source on contact-probe cutoff.

---

## 3. Does LANTERN have a chain-of-command / decision-authority concept (matcher → policy → estimate), fallback, abort or ground-in-the-loop?

### Takeaway
Yes, but only for **measurement acceptance**, never for vehicle actions. Both Unity and Python implement a strict one-way veto hierarchy: sensor/matcher validity → geometric gate → optional learned veto or gain → state update. Learned components can only *reduce* authority, and they fail closed. No component can abort, hold, retarget (except the scripted Python divert) or hand control to a fallback guidance mode. There is no ground loop.

### Cited Findings

**Unity authority chain (estimated-state experiments)**
1. `LocalScanMatcher.Match` sets `valid`: ≥ 80 points and inside the map — REPO `TerrainNavigationCore.cs:54,63`.
2. The same function sets `accepted` = ¬boundary ∧ RMS ≤ 8 ∧ conf ≥ 0.35 — `TerrainNavigationCore.cs:80`.
3. The arm policy decides:
   - `ScanUtilityPolicy.Gain` returns 0 if ¬valid or ¬accepted, 0 for `off`/`collect`, and 0 for a non-finite prediction (`bounded` excepted) — REPO `ScanUtilityPolicy.cs:59-62`.
   - `PortableScanTrust.Accept/RuleAccept` require `m.valid && m.accepted` — `PortableScanTrust.cs:89-92`.
   - Models are schema-checked at load and rejected if malformed — `ScanUtilityPolicy.cs:14-31`; `PortableScanTrust.cs:27-62`.
4. `nav.Correct(gated)` applies g·correction to position — `ScanUtilityRunner.cs:305-306`.
5. Guidance consumes the estimate. Truth is used only for logging and labels; this is stated in comments and implemented by passing only `ScanMatch` + AGL to the policy — `ScanUtilityRunner.cs:297-303`; `TerrainNavigationCore.cs:7,100`.

**Python authority chain**
- Altimeter: availability → judge (χ²; tolerance; physical-possibility "impossible" → immediate reject; "surprising" → probation buffer of K samples, accepted as one mean-innovation update only if self-consistent) → EKF scalar update with judge-chosen R — REPO `engine.py:362-481`.
  - "Second opinion" accepts a surprising reading only if the IMU-vs-altimeter rate jump > 20 m/s and the last camera fix was consistent — `engine.py:410-420`.
  - Cautious mode widens the gate (χ² 10.83) when the map is missing — `engine.py:398`.
  - The `pitfal` judge inflates R ×10 for 40 samples (10 s) after a flag — `engine.py:371-378`. Inference: despite the name, this is a single-beam χ²-plus-inflation rule, not the multi-beam consensus of the published PITFAL (PRIOR-AUDIT describes PITFAL as multi-beam slant-range consensus).
- Camera: matcher confidence gate peak ≥ 0.5 and/or Sun-geometry lit-fraction weighting → EKF update — `engine.py:517-534`.
- Scan: a three-way check rejects a fix that disagrees with a confident estimate by > 4σ + 50 m — `engine.py:550-556`.
- Python learned scan veto: "cannot promote a geometrically rejected scan"; invalid features or inference failure → reject — `sim/scan_trust.py:27-32,54-72`.

**Fallbacks present**
- Unity: implicit inertial coasting when scans are rejected. It is harmless because the IMU is near-perfect (Q2).
- Python: coarse global-topography reference and, in v2, an α-β terrain-relative altitude filter for the final 200 m when the map is missing — REPO `engine.py:234-238,255-258,283-286,485-489`; `world.py:184-187`.

**Absent**
- Abort, hover/hold, re-designation, safe mode, sensor-voting across redundant units, actuator FDIR, and ground uplink or go/no-go. A keyword grep for abort / safe mode / FDIR / uplink / mode-manager / cutoff / throttle-lag across `sim/`, `LANTERN/Assets/Scripts`, `LANTERN/Assets/Editor` found no implementation (REPO, grep).
- Terminations are evaluation outcomes: timeout 360 s / 800 s; out-of-bounds ±1000 m in Unity — `ShortDescentExperiment.cs:326-327`; `engine.py:35,572-576`.

### Inferences
- LANTERN's "chain of command" is a measurement-level authority hierarchy (geometry outranks learning; learning can only veto or shrink). That is a sound, flight-like design principle, but it is untested at the system level: nothing escalates. A real FDIR design would ask "what does the vehicle do after N consecutive rejected scans, or when residuals stay large?" (hold, retarget, widen search, switch to velocity-only terminal mode). LANTERN cannot study that question yet.
- Unity has no covariance, so the "policy" cannot weigh matcher confidence against the estimate's own confidence. Python can (S = HPHᵀ + R), which is why Python's acceptance logic is the more transferable result.

### Gaps
- No documentation in the repo states an intended authority hierarchy beyond code comments. I did not search every doc for design intent; this is inferred from code.

---

## 4. Which LANTERN conclusions are robust to these gaps, and which could change?

### Takeaway
- **Robust**: shifted-map 0/N failures (structural observability, independent of GNC fidelity); the qualitative finding that geometric acceptance metrics mispredict closed-loop outcomes; and the design rule that learned layers should only veto.
- **Fragile**: the Unity horizontal-speed violations and the "utility lowers miss but raises violations" trade-off, because they are produced by a guidance law with no terminal velocity-nulling phase; the aligned ≈ 100 % success level; and absolute fuel and touchdown-velocity numbers.
- **Intermediate**: Python altimeter-trust rankings. They come from a real EKF and terminal phase, but a 4 Hz loop with perfect actuators and synthetic faults.

### Cited Findings
- Speed-violation evidence: all utility violations occurred under changed terrain. Expanded v2 had 69/90 changed-terrain ON contacts > 1 m/s (max 6.83 m/s) and 0 aligned — REPO `docs/SCAN_UTILITY_RESULTS.md:53-58`; `docs/SCAN_UTILITY_TRANSFER_RESULTS.md:49-52`; `docs/TERRAIN_MATCHING_EXPANDED_RESULTS.md:26-30` (PRIOR-AUDIT).
- Mechanism ingredients (REPO):
  - the correction changes position only — `TerrainNavigationCore.cs:94-95`;
  - guidance keeps position tracking (−0.04x̂) down to contact — `:105-107`;
  - scans stop at 80 m — `ShortDescentExperiment.cs:310`;
  - the threshold is v_h < 1 m/s — `:332`.
- The Python guidance commands v_h → 0 below 60 m estimated AGL with a 2 s time constant, and its threshold is v_h ≤ 1.5 m/s — REPO `engine.py:268,270,306`.
- Apollo P66 controlled velocity only, from about 30 m — SNIPPET (Klumpp R-695). ALHAT vertical descent from about 30 m — PRIOR-AUDIT.

### Inferences

**Horizontal-speed violations: likely to change substantially (COMPUTED + inference).**
- The Unity horizontal loop has poles at −0.1 and −0.4 s⁻¹. A position step Δ produces a peak lateral speed ≈ 0.063Δ and leaves ≈ 0.02Δ after the ~19 s from the last scan to contact (PRIOR-AUDIT derivation).
- With a P66-style terminal phase (drop the position term, null v_h with a ~2 s time constant from ~30–80 m), the residual after ~19 s would fall roughly as e^(−19/2) ≈ 10⁻⁴ of the speed at phase entry. For the Python-like 60 m gate, the residual would be governed by velocity-estimate error rather than by the correction history.
- Expected effect: most changed-terrain v_h violations would disappear, and the utility-vs-geometric difference in violation counts would likely shrink or vanish. Miss distance would change little, because scans already stop at 80 m; the touchdown point would freeze near where the estimate stood at phase entry.
- **Conclusion at risk**: "partial gains / learned utility increase speed violations". It should be reported as conditional on a position-tracking-to-contact guidance law.
- Opposite-direction effect: adding realistic tilt/attitude lag and throttle dynamics (absent everywhere) would slow both the transient build-up and its nulling. The net sign is unknown without simulation.

**Perfect velocity (Unity).**
- Touchdown v_h is purely guidance-generated. With a real IMU (bias ~ μg–mg, attitude errors) and no velocimeter, velocity errors would add a TRN-independent v_h floor and make rejection costly (drift grows). Inference: conservative/reject-heavy arms (`off`, strict vetoes) are flattered today, because rejection costs nothing beyond keeping the initial constant offset. With a drifting IMU, the v1 finding that the ML veto hurts (18/162 vs 90/162, PRIOR-AUDIT) would probably get *stronger*, and gain-scheduling comparisons could reorder.

**Perfect attitude / instantaneous scans (Unity).**
- COMPUTED: horizontal point-placement error ≈ AGL·δθ, i.e. 0.87 m per 0.1° and 8.7 m per 1° at 500 m, and 3× that at 1500 m.
- Aligned-map success (≈100 %) would likely fall once attitude knowledge errors of ≳0.5° are added. Changed-terrain RMS/confidence distributions would shift, so the geometric thresholds (RMS 8 m, conf 0.35) and any learned model trained on them would need re-validation.
- Scan latency: with |v_h| ≈ 0 in Unity, motion during a scan is mostly vertical (10–30 m/s), and the mean-removed cost is insensitive to it. Latency would matter more under a real approach with horizontal velocity, as in the Python start at 100 m/s.

**No covariance filter (Unity).**
- Any conclusion of the form "learned gain beats fixed gain" is relative to a hard-reset baseline. Against a KF with matcher-derived R and χ² gating, the margin is unknown (PRIOR-AUDIT recommends these baselines). Python results, which have that structure, are the better evidence for the trust-layer concept.

**Touchdown definition.**
- Both estimated-state paths assume powered contact at ≈ 0.5–0.7 m/s with instantaneous cutoff (implicit by episode end). Results are internally consistent. They would not transfer to a lander that cuts off at a few metres: COMPUTED +3.1 m/s from 3 m would fail v_z < 2 regardless of navigation. Python's slope ≤ 10° check is the only terrain-safety criterion; Unity has none.

**Shifted-map 0/N: robust.**
- The derivation (absolute miss = |s| = 38–47 m > 10 m, PRIOR-AUDIT) depends only on map-relative matching and the absolute-frame metric, not on guidance, actuators or attitude. No GNC upgrade changes it short of an independent absolute reference.

**Map-condition ordering (aligned > changed > shifted): robust qualitatively.**
- Exact changed-terrain success rates (6/18; 0/54) are fragile. They depend on the guidance-generated v_h criterion analysed above: many changed-terrain failures are speed violations, not misses.

**Python altimeter-trust results: moderately robust.**
- Real EKF, bias state, χ² gating, delay modelling, a terminal phase and 500-run batches (`pipeline.py:22`) make them the most GNC-credible LANTERN results.
- Caveats:
  - The 4 Hz single-rate loop under-samples real IMU/attitude dynamics; inference: probably small for altimeter gating.
  - The IMU sees commanded acceleration, so thrust errors are not dispersed. ALHAT dispersed thrust/Isp/mass (PRIOR-AUDIT).
  - Fault bursts are synthetic biases.
  - The scan fix is synthetic, not the real matcher. Python "trust_scan" results say nothing about matcher failure modes.

**Full-height demo.**
- Supports only "the 6-DOF vehicle and autopilot can land from 102.5 km on true state at 0.50 m/s" (`runs_summary.csv:2`; `README.md:61`). It provides no evidence for navigation or TRN in the loop, as the project itself states (`docs/PROJECT_EXPLAINED_AND_REFOCUSED.md:86-87,107-109`). Its free fall from rest at 102.5 km is not a real lunar descent profile: real descents start powered braking from orbital horizontal speed (inference; Chang'e-3 braking from ~15 km, SNIPPET).

### Gaps
- None of these sensitivities has been simulated. The terminal-phase, attitude-error, IMU-bias and actuator-lag effects are predictions from code and linear analysis.
- Recommended discriminating ablations: (1) a velocity-only terminal phase below 30/60/80 m; (2) an IMU bias plus attitude-knowledge error coupled into point placement; (3) a first-order throttle/tilt lag of 0.2–1 s; (4) a KF with χ² gating replacing the overwrite; (5) cutoff-at-height touchdown variants.
