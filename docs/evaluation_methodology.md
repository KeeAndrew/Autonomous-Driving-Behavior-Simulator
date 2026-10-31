# Evaluation methodology

Full mode evaluates exactly 10,000 held-out scenarios per controller (30,000 controller runs), independent of training and validation scenarios. All controllers receive identical scenario initial conditions, actor motion, visibility rules, target speed, destination, time limit, physics, collision detection, and metric definitions. Teacher demonstrations and validation runs are additional work and are not counted as held-out evaluation.

## Safety

- Collision: at least one swept footprint overlap, with episode terminated at first collision. Rate = collided scenarios / scenarios.
- Minimum separation: minimum sampled Euclidean clearance between ego rectangle and any actor rectangle, including hidden actors. Collision detected between endpoints can yield a positive endpoint separation; collision itself remains authoritative.
- TTC: current footprint gap / positive closing velocity for a visible, laterally overlapping front vehicle; infinity if nonclosing. Minimum TTC is taken across all frames. No finite TTC is fabricated. Features/clustering use a 30 s cap; aggregate report labels capped mean explicitly.
- Near-miss episodes: a rising edge of noncollision and (separation<1 m OR TTC<1.5 s). Collision frames are excluded, although a scenario may have an earlier near miss and later collision. This is episode frequency, not number of frames.

## Efficiency

Distance = final longitudinal x relative to x=0 start; average speed = distance / actual elapsed simulation time. Arrival is elapsed time if destination reached without collision, otherwise infinity. Completion is a binary successful arrival within duration. Progress = min(distance/destination,1). Report arrival mean only over completions, alongside completion and collision rates to avoid survivorship misinterpretation. Duration truncation and collisions cause shorter trajectories; do not compare average speeds without those outcomes.

## Braking and comfort

Hard braking begins when actual longitudinal acceleration crosses below -4 m/s²; consecutive below-threshold timesteps count as a single episode. Leaving then re-entering the threshold starts another episode (no debounce/hysteresis). Braking time sums dt for actual acceleration< -0.1 m/s². Peak deceleration=max(-acceleration,0). Per-kilometer rates in the report use total events / total distance in km, not the mean of scenario-normalized rates. Individual zero-distance scenario rates are infinity.

Longitudinal jerk=(a_next-a_previous)/dt, with initial a=0. RMS jerk = sqrt(sum(jerk² dt)/elapsed). Acceleration variance=sum(a² dt)/elapsed-[sum(a dt)/elapsed]², clamped nonnegative for rounding. Lateral jerk uses lateral acceleration differences with identical weighting. Saturation/stop discontinuities remain visible in comfort metrics. Metrics integrate every timestep even when exported telemetry is downsampled.

## Divergence

Pair baseline and ML telemetry on scenario ID and exact fixed-step time; reject duplicate keys, mismatched scenario IDs/kinds, and missing common prefixes. Let the common sampled prefix have n observations:

- Acceleration command disagreement: sqrt(sum((a_ML-a_base)²)/n).
- Trajectory disagreement: sqrt(sum((x_ML-x_base)²+(y_ML-y_base)²)/n).
- Lane disagreement: fraction of paired samples with different desired lane.

A scenario is selected when acceleration RMS>=1 m/s² OR trajectory RMS>=5 m OR lane disagreement>=0.1 OR binary collision outcomes differ. Thresholds are declared before evaluation and never adjusted to achieve a record target. Exactly one selected row per scenario; no duplication. Common-prefix comparisons stop at the shorter rollout, so full outcome differences are also retained. The threshold cannot compensate for unobserved post-collision decisions. Full mode samples telemetry every 10 steps (0.5 s); metrics use every .05 s. Quantization can miss short-lived disagreements and must be acknowledged.

Clustering vectors contain acceleration RMS, trajectory RMS, lane disagreement, ML-minus-baseline minimum following clearance, capped minimum TTC, hard-brake count, progress, and RMS jerk. This is descriptive outcome analysis, never an input to model training. StandardScaler is fit on the selected set. K-Means explores k=2..8, records inertia and deterministic sampled silhouettes, and chooses maximum silhouette. DBSCAN tries four k-distance quantiles (50/70/85/95%), min_samples=min(n,max(5,2d)), records noise and non-noise silhouette, and picks highest available silhouette. Noise remains -1. Silhouette uses at most 1,500 points for cost; all records are assigned. Degenerate data produces an explicit insufficient-data result rather than invented clusters.

PCA projections illustrate clusters but do not determine them. Physical-unit cluster means and category proportions interpret actual groups; labels are not assumed to match scenario strata. Adjusted Rand index compares assignments, including DBSCAN noise as a label. DBSCAN can require quadratic memory for dense neighborhoods; larger future experiments should consider bounded-neighbor algorithms or an explicitly reported subsample.

## Hybrid evidence, uncertainty and integrity

Validation baseline/ML differences and clusters are generated before held-out execution. `hybrid_design.json` records ML collision wins/losses, hypotheses, and controller source hash. The hybrid's thresholds are predeclared engineering choices. Validation findings can motivate those rules but do not establish a causal derivation; no tuning to held-out data is allowed. Future changes require a new evaluation seed/corpus to retain a clean holdout.

Reduction percent=100(base-other)/base; null when baseline is zero. Negative reductions are regressions. Paired bootstrap samples whole scenario IDs with replacement, using seed 61 and 1,000 replicates. Report 2.5/97.5 percentiles for mean differences and relative reductions; omit relative-reduction replicates with zero baseline denominator and report the count. Pairing preserves correlated scenario difficulty. These intervals describe this synthetic scenario distribution, not simulation/model bias. Early termination can reduce observed hard-braking opportunities; interpret event counts together with distance, collision, completion, and time.

Results contain dataset/model/input hashes and an exact dependency snapshot. Floating point and library version changes can shift borderline outcomes across machines; replay is deterministic within the recorded configuration, not a bitwise cross-architecture guarantee. Small failure-derived regression fixtures protect observed outcomes on the verified toolchain.