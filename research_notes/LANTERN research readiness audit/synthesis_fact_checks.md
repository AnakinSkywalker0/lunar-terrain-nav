# Targeted local fact checks during synthesis

25 October 2026. Direct source reads only; no simulations, tests, retraining or fixes executed. These checks resolve a few questions left open by the three completed notes without expanding into another source audit.

## Legacy classifier producer and feature boundary

[`sim/pipeline.py:105–131`](../../sim/pipeline.py#L105-L131) collects procedural-world observations grouped by world seed, holds out the last world seed, fits a 120-tree random forest (depth 14, minimum leaf 20, random state 0), evaluates it, then refits on all training worlds. The seed list is 21–26 at [lines 24–25](../../sim/pipeline.py#L24-L25). This establishes the current producer's intended world-group split and refit, not historical input identity or independent reproduction of stored AUROC. Collection is restricted to available high-innovation PITFAL-path observations at [`engine.py:490–495`](../../sim/engine.py#L490-L495), not all sensor samples.

The misleading formal argument `agl_true` in `_features` receives `r_meas` at both inference and collection call sites ([423](../../sim/engine.py#L423), [494](../../sim/engine.py#L494)). Therefore this argument name is not evidence of truth-altitude leakage. Other map-access inconsistencies remain as described in the implementation note.

## Legacy fault-metric denominators

[`engine.py:453–480`](../../sim/engine.py#L453-L480) counts individual direct decisions and the component readings of resolved probation windows. [`engine.py:622–625`](../../sim/engine.py#L622-L625) computes false rejection as summed valid-rejected/summed valid-total and missed fault as summed faulty-accepted/summed faulty-total. These are reading-level bookkeeping rates, not the percentage of missions fooled. Unresolved probation samples are not flushed into these counters at timeout ([572–578](../../sim/engine.py#L572-L578)). Fault labels compare measured range with current true range against a range-dependent threshold ([335](../../sim/engine.py#L335)); latency disagreement is consequently part of the labelled error under that definition. Exact raw numerator/denominator totals were not recalculated in synthesis.

## Legacy scenario filename collision mechanism

[`pipeline.py:85–89`](../../sim/pipeline.py#L85-L89) names per-run files using only `sc.name.split()[0]` plus judge and optional tag. The main batch schedules both cliff scenarios with the same directory and no tag ([168–180](../../sim/pipeline.py#L168-L180)). This is a source-visible collision hazard consistent with the experiments note's independently established two-summary/one-prefix archive gap. It does not reconstruct the timing/order of historical overwrites. Preserve missing raw coverage as unresolved until recovered or rerun.

## Matcher and controller equations

[`TerrainNavigationCore.cs:37–80`](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L37-L80) minimizes variance of height residuals, searches horizontal shift, and uses mean distant coarse costs for confidence. [Lines 86–108](../../LANTERN/Assets/Scripts/Experiments/TerrainNavigationCore.cs#L86-L108) implement a position/velocity integrator, height overwrite, position correction and proportional/velocity-feedback guidance. Before force clipping, a horizontal position correction `alpha*c` changes commanded horizontal acceleration by `-0.04*alpha*c`; it does not directly correct velocity. This motivates, but does not establish, the proposed control-risk mechanism.
