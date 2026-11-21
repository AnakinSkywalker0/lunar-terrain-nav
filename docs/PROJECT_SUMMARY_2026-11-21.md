# LANTERN project summary (21 Nov 2026)

One-page record of everything done up to 21 Nov 2026. Longer sources are named in each section. Simulation only; every vehicle and beam-geometry number that is not from NASA data is assumed.

## What the project is
A lunar lander's navigation filter must decide which sensor readings to trust. HAKUTO-R (2023) rejected valid altimeter data at a crater rim; IM-2 (2025) trusted a camera in shadow. LANTERN is a Unity lander testbed plus a fast batched Python simulator (`sim/engine.py`) on real NASA PGDA terrain (Site04, Site01; `data/`, not in git) and procedural worlds. Team: Abhishek Mishra (240365), Rishabh Kumar (240605), Neil Jain (240553), Khushi Vijay (240511); mentor Dr. Sukhandeep Kaur, Professor; BML Munjal University Project-I, Aug to Dec 2026.

## Timeline
| Date | What |
|---|---|
| 18 to 21 Oct | Unity testbed, Python bench, camera survey, rounds 1 and 2 (tags `round1`, `prereg-round2`); `docs/FULL_LOG.md`, `PREREG.md` |
| 22 Oct | Unity-side scan trust, scan utility (and its Site01 transfer), terrain matching, novelty review |
| 29 Oct | Literature verification (`reports/`, `research_notes/`) |
| 4 to 9 Nov | Navigation v3 prototype, guidance ablation (headless Unity) |
| 19 to 20 Nov | ml-eval study merged; round 3 frozen (`prereg-round3`) and run once on Site04; round 4 frozen and run on worlds 17-20; world-12 diagnosis |
| 21 Nov | Round 5 (eleven techniques, held-out worlds 41-50); round 6 (6-DOF dynamics); college report (51 pages), handoff package; real flight-data search |

## Results that hold (pre-registered, run once)
* **Round 3, Site04 (5 of 5 rules met):** the noise floor takes the tolerance gate from 62% to 95% at x8 noise (PITFAL-style 66%, trust v2 89%); +48 points over plain tolerance at x16. `docs/ROUND3_RESULTS.md`.
* **Round 4, worlds 17-20 (2 of 4 met):** candidate B failed R1 and R2; the floor in both places (A) did not collapse; single-beam floor +12.5 with a 100 m map offset. `docs/ROUND4_RESULTS.md`.
* **Round 5, worlds 41-50 (5 of 7 met):** Student-t weighting within 3 points of PITFAL-style at low noise and +19 to +21 at x16 (three beams); delay estimation without time stamps 1.5% to 51%; Student-t did not beat the full floor at low noise (S3) and soft camera was 0.2 points short at cliff (S6). `docs/ROUND5_RESULTS.md`.

## Exploratory findings
* Round 5 development: IMM-style noise modes, Student-t, delay estimation, soft camera weighting helped; joint update, learned gate selector, conformal limits, solution separation did not; CUSUM hurt. `docs/ROUND5_DEV_RESULTS.md`.
* Round 6, 6-DOF dynamics (`sim/dyn6.py`, switch `dyn6=` in the engine, default off, bit-identical when off): with a working attitude loop the rule ranking holds (three beams x16: floor and Student-t about +30 over PITFAL-style); Student-t's low-noise edge disappears; single-beam landing is lower than in 3-DOF; a sluggish or badly sensed vehicle fails for every rule. `docs/ROUND6_DYN6_RESULTS.md`.

## Not solved
2 km wrong map (at most 5% held-out); delays without stamps (51% vs 90% with true stamps); second real site; real sensor data; B5 (point-mass filter) and B6 (learned gain) not built.

## Real flight data (web search, nothing downloaded)
Raw descent telemetry is not public for modern landers. Public: Chandrayaan-3 science data on ISRO PRADAN (descent telemetry not confirmed), Morpheus/ALHAT papers on NASA NTRS, Apollo guidance source code, IM-1 press reports. Check each source before relying on it.

## Evidence rules
Tags `round1`, `prereg-round2` to `prereg-round5`; held-out and Site04 data used up (see the vault note or `docs/PREREG_ROUND*.md`): Site04 (rounds 2, 3), worlds 17-20 (round 4), 27-32 (round 5 training), 41-50 (round 5). A new confirmatory test needs fresh worlds and a new pre-registration.

## Deliverables and open items
* `report/LANTERN_Project_Report.docx` and `.pdf` (rounds 1 to 5; round 6 not yet in it), `handoff/LANTERN_Handoff_Report.pdf` and `LANTERN_Handoff_Package.zip` (before round 6).
* Open: Neil's and Khushi's contribution lines (assigned by the assistant, must be confirmed), supervisor signature, plagiarism report page, AI-use statement check, "PROJECT-IV" vs "PROJECT-I" on the front page.
* Deadlines: final draft + plagiarism report 27 Nov 2026; printed signed report 2 Dec 2026.
* Next candidate step: pre-register the full floor against Student-t and PITFAL-style on fresh worlds plus a second real site (needs approval to download NASA data).

## What is not in git (kept locally, regenerable)
Raw per-descent dumps of the October to November Unity experiments (`descent_*.csv`, `stationary_*.csv`, `map_*.bin`, `reserved_*` under `out/guidance_ablation`, `out/scan_utility`, `out/scan_utility_transfer`, `out/scan_trust`, `out/terrain_matching`, `out/navigation_v3`; about 1.3 GB, 39,000 files), large `scans.csv` / `sensors.csv` files, `*.raw` height maps, downloaded paper PDFs under `out/literature` (public NASA/NTRS documents), report build intermediates, `.claude/settings.local.json` and `LANTERN/.mcp.json` (machine-specific). Summaries, tables and figures of those experiments are in git. NASA GeoTIFFs in `data/` stay out as before (see README).
