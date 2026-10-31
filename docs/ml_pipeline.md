# ML pipeline and inference contract

## Provenance and labels

Training uses only independently generated training scenario IDs (0 upward, seed 1001). Validation uses IDs 100000 upward, seed 2001. Evaluation uses IDs 200000 upward, seed 3001. Split assignment occurs before any rollout. Training and validation files must be explicit teacher telemetry with disjoint scenario IDs. Rows from the same rollout never cross splits. Nearby timesteps remain correlated; validation by scenario avoids presenting this correlation as independent generalization.

The teacher is implemented in `src\controllers\controllers.cpp` and documented in controller design. Its acceleration on the current observable state is the regression label. No future collision, scripted braking time, elapsed simulation time, actor visibility time, scenario kind, evaluation outcome, or future trajectory enters the features or target. Training models *imitation*, not reinforcement learning and not learning from production logs. Every datum is synthetic.

## Feature schema (version 1)

Order is fixed across `Observation::features` and `python.common.FEATURES`:

| Index | Feature | Unit / cap |
|---:|---|---|
| 0 | ego speed | m/s |
| 1 | target speed | m/s |
| 2 | visible lead footprint clearance | m, clipped [0,250] |
| 3 | lead speed (ego speed if no lead) | m/s |
| 4 | closing speed = ego - lead | m/s |
| 5 | TTC | s, maximum 30 including infinity |
| 6 | pedestrian longitudinal gap | m, clipped [0,250] |
| 7 | estimated pedestrian entry time | s, clipped [0,20] |
| 8 | adjacent front clearance | m, maximum 250 |
| 9 | adjacent rear clearance | m, maximum 250 |
| 10 | adjacent rear closing speed | m/s |
| 11 | current effective ego acceleration | m/s² |

Trees need no standardization; these physical-unit feature caps are the complete runtime preprocessing. Clustering separately uses StandardScaler on behavioral differences. Missing feature names or nonfinite training data fail explicitly.

## Training and evaluation

RandomForestRegressor: 32 trees, maximum depth 10, minimum leaf size 8, all features at each split, seed 41, parallel training. These fixed hyperparameters trade approximation quality against runtime size. They are not tuned on held-out outcomes. Full demonstrations sample every fifth timestep (0.25 s) from 1,200 train and 400 validation scenarios. Validation MAE and RMSE are reported in m/s². They measure one-step imitation accuracy, not closed-loop driving safety. The model can visit states absent from teacher trajectories and accumulate error; this covariate shift must be judged using closed-loop evaluation.

The exporter writes an ASCII `.forest` containing a versioned header and every regression tree node. Each node contains left/right child, feature, double threshold, and scalar value. Leaves use -1 child indices and feature -2. C++ bounds counts, rejects cycles/backward child links, and rejects nonfinite fields. Forest prediction averages leaf values, clips acceleration, and passes it through shared dynamics. It has no Python or ONNX dependency at runtime. The `.joblib` file is only a Python training artifact; do not load untrusted pickle/joblib files.

Scikit-learn casts features to float32 before comparing them to double thresholds. C++ explicitly reproduces that cast, including <= branch selection. Training verifies parity on up to 1,000 validation rows plus split thresholds and neighboring float32 values. Unit tests independently train/export a small forest and compare C++ predictions at tolerance 1e-10. Model and dataset hashes plus environment lock files support reproducibility.

## Tradeoffs

ONNX Runtime could handle more model families and optimized hardware kernels but adds native binary packaging, architecture/version concerns, and operator compatibility checks. A small forest is straightforward to audit, portable, and fast enough for this workload; text storage is larger than binary and schema changes require coordinated updates. There is no learned lane classifier; keeping baseline lane decisions isolates longitudinal changes. Baseline fallback on a runtime prediction exception is conservative engineering behavior, not a safety proof. Invalid or absent models fail at startup.