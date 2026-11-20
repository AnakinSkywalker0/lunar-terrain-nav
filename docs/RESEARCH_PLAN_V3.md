# LANTERN research plan v3 (4 Nov 2026)

> **Status update, 8 Nov 2026.** Gates were run headlessly (see `GUIDANCE_ABLATION_RESULTS.md`). G1: mixed/persists. G2 (authority gate):
> not supported; hypothesis H1 is largely rejected (violations occur only when fixes are wrong). G3: a classical Kalman + chi-square gate
> beat geometric matching and the learned policy on 12 areas. The plan below is kept as written for the record.

Status: proposal. Nothing here is a result. Evidence labels: [CODE] read in repo, [DATA] computed from
existing run files, [SEARCH] seen only as a search snippet (full text NOT read), [UNVERIFIED].

## 1. What the literature check did and did not establish
Scope: about 10 web searches plus the local 29 Oct source set. Not exhaustive. "Every paper that
exists" cannot be checked. Two page fetches failed (Springer paywall, Stanford certificate error).

Found [SEARCH]:
- Learned per-match, non-Gaussian TRN uncertainty on real data exists: Acharya et al., RA-L 2025 (arXiv 2405.20513).
- TRN failure detection and recovery frameworks exist: Houts, Dektor, Rock 2013 (Stanford ARL); an EKF-TRN
  integrity architecture with protection levels exists for radar-altimeter UAV TRN (KAIST). Neither is lunar landing.
- Mars 2020 books reference-map error inside targeting error (NTRS 20230007014).
- One search result mentions Apollo-era analysis where large navigation-driven changes push command rates
  near control limits. Not opened. [UNVERIFIED]
- No search found a paper that judges TRN-fix acceptance by closed-loop touchdown velocity, or one that
  gates TRN fixes by whether guidance can still absorb them. This is absence in a limited search, not proof.

Consequence: "learned trust" and "fault detection" are not novel. A narrower question remains open as far as I could see.

## 2. Evidence from our own data (new, this session)
- [CODE] Guidance: horizontal accel = -0.04*pos - 0.5*vel, clamped to ay*tan(10 deg), about 0.365 m/s^2
  (TerrainNavigationCore.cs:98-109). Lateral authority is small and fixed.
- [CODE] A replica of that law (ideal vertical tracking, 80 m AGL start) predicts contact vh of roughly
  0.047 per metre of step, i.e. vh >= 1 m/s for steps above ~25-30 m. This is a prediction, not a result.
- [DATA] It does not match the sim cleanly: many non-violating relief runs had ~60 m estimate jumps.
  So the simple model is incomplete.
- [DATA] Time spent at the tilt limit in the last 20 s correlates with contact vh (Spearman 0.46 to 0.64
  across geometric, bounded, utility on relief_positive); the controller's position offset does not
  (-0.10 to 0.49). Small n, clustered by terrain area. Suggestive only.
- [DATA] Re-scoring shows the shifted-map 0/54 was a frame artifact; 18 shifted failures are all start
  error u2 (~95 m), likely a matcher search-window edge. [inference]

## 3. The one hypothesis worth testing
H1: Speed violations after a terrain fix come from limited lateral authority (tilt clamp) and short
time-to-go, not from the matcher being wrong. A gate that accepts a fix only as far as guidance can still
null it (reachability / authority-aware blending) should cut violations without losing position gain.

Why it could be worth a paper: it is physical, cheap to test in the existing Unity sim, comparable to
classical baselines, and independent of any learned model. If H1 fails, the null result is still reportable.

## 4. Kill gates (decided before running)
G0 (offline, done): saturation tracks violations. Passed weakly.
G1: add a terminal velocity-nulling phase to guidance. If violations under relief drop to near the
    no-correction level, the speed story is a controller artifact -> STOP H1, keep only the evaluation-frame note.
G2: authority-aware blending vs accept-all, hard bound (existing "bounded"), and geometric, paired runs,
    same seeds and start errors. Pass if violations fall >=30% with mean map-relative miss not worse than
    geometric, evaluated with terrain area as the unit (>=10 areas).
G3: beats a tuned Kalman + chi-square gate with equal tuning budget. If not, report as negative.

## 5. Work order
1. Fix rescoring: drop per-run CIs, cluster by area, report both frames at 10/50/100 m. [tools/rescore_thresholds.py]
2. Headless runner: exit hook, stage entry points. [HeadlessEntry.cs]
3. G1 experiment (guidance variant, relief + shift, headless).
4. Only if G1 shows persistence: G2 arms, more areas, realistic map-error model (horizontal tie error
   0.1-10 m labelled realistic; larger shifts labelled gross; PGDA clones only for vertical error, availability unchecked).
5. Fix wrong claims in docs (IM-1, IM-2, 90 m, Choe 2022 citation) and README "unsolved" wording.

## 6. Not promised
No result is guaranteed. The point of the gates is to find out in days whether there is a paper, not weeks.
