# Verified results — October 31, 2026

Actual Windows executions in the existing repository. These results are synthetic simulation measurements, not real-world safety evidence. Both Smoke and Full pipelines completed. No source parameters were tuned to the held-out outcomes. Smoke evaluation is a prefix of the full evaluation corpus; it verified software execution, and was not used to tune controller thresholds.

## Environment and verification

- Host: Windows build 26300, ARM64; PowerShell 7.6.5; Git 2.54.0.windows.1.
- Installed with approval: Visual Studio Build Tools 2022 17.14.44, MSVC 19.44.35229.0, Windows SDK 10.0.26100.0, CMake 4.4.4.
- Verified configuration: `vs2022-x64` / `release-x64`, MSVC ARM64-hosted compiler targeting Windows x64, executing through Windows ARM64 emulation. No Linux/WSL/container substitution.
- Python: existing bundled CPython 3.12.14 AMD64, local `.venv`; exact installed packages are in `requirements-windows-x64.lock.txt` and the per-run environment snapshot.
- Native ARM64 target installation failed: Visual Studio returned 5007 without elevation, then 8006 due to missing channel feed. ARM64 presets are supplied, but not verified. Use the verified x64 configuration, or complete ARM64 installation through Visual Studio Installer.
- Final Release build succeeded, with no compiler warnings emitted. CTest: 1/1 suite passed, containing 2,230 explicit contract checks. Python: 13 passed, zero failed, zero skipped after capture of regression fixtures.
- Sixteen actual validation divergence cases are tracked in `data/sample_scenarios/regressions.csv` with provenance and baseline/hybrid expectations. Tests do not auto-update snapshots.
- Independent tests cover tree inference parity, deterministic replay, dynamics/limits, TTC, footprint collision, swept vehicle/pedestrian collision, exact braking/comfort metrics, pedestrian decisions, lane acceptance, invalid inputs, and failure-derived replay.
- Initial Python runs skipped the not-yet-captured regression fixture; this was resolved before final verification. The smoke rerun from `docs` verifies script-relative root resolution and rerunnability.

## Dataset and model

- Training: 1,200 scenarios, 48,156 teacher demonstration rows; validation: 400 scenarios, 15,482 demonstration rows.
- Validation acceleration MAE: 0.107303 m/s²; RMSE: 0.393184 m/s².
- Python/C++ inference parity: 4,117 validation/boundary cases, maximum absolute error 1.78e-15 m/s² (tolerance 1e-10).
- Validation baseline/ML collision comparisons: 34 ML wins and 38 losses. The hybrid is a predeclared interpretable hypothesis, not an automatic discovery or evidence of aggregate ML safety superiority.
- Held-out: 10,000 scenarios per controller, 30,000 runs. Equal allocation across eight scenario strata; seeds 1001/2001/3001 for train/validation/evaluation.

## Measured comparison

| Controller | Collisions | Collision rate | Hard-brake events | Events/km | Completion | Mean RMS jerk (m/s³) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 2,997 | 29.97% | 8,192 | 5.114 | 62.72% | 4.259 |
| ml | 3,000 | 30.00% | 4,100 | 2.686 | 51.38% | 2.946 |
| hybrid | 2,639 | 26.39% | 8,881 | 5.587 | 58.98% | 3.821 |

Positive reduction means fewer events. Negative reduction is a regression:

- ml, collision: reduction -0.1001%; paired bootstrap 95% interval [-3.1199%, 2.6566%].
- ml, hard_brakes: reduction 49.9512%; paired bootstrap 95% interval [48.6205%, 51.1755%].
- hybrid, collision: reduction 11.9453%; paired bootstrap 95% interval [9.2815%, 14.4142%].
- hybrid, hard_brakes: reduction -8.4106%; paired bootstrap 95% interval [-11.4306%, -5.1656%].

Hybrid reduced collisions but increased hard-braking events and reduced completion. ML cut braking and jerk, but had nearly unchanged collisions and lower completion. The original 25% collision and 18% braking improvements were not achieved and must not be claimed. Improvements are specific to this synthetic distribution and baseline. Higher event rates per kilometer also show that hybrid braking cost cannot be explained away by its raw event count alone.

## Behavioral divergence and clustering

- Selected 9,243 unique actual evaluation divergences using unchanged thresholds. No duplicated records or threshold relaxation. This exceeds the requested 1,500-record capability.
- K-Means: explored k=2..8; selected k=5 by maximum deterministic sampled silhouette.
- DBSCAN: selected 10 groups, noise 17.29%; eps=0.96220, min_samples=16.
- Cluster meanings are based on actual physical-unit difference means and scenario proportions, not assumptions that four semantic categories must appear. See the generated findings and profiles.

## Artifact locations (relative to repository root)

- `results/full/evaluation/report.md`, `report.json`, `comparison.csv`, `comparison.png`: measured outcomes and paired bootstrap intervals.
- `results/full/evaluation/baseline_metrics.csv`, `ml_metrics.csv`, `hybrid_metrics.csv`: per-scenario metrics; corresponding `_telemetry.csv` files contain sampled trajectories/observations.
- `results/full/evaluation/paired.csv`, `divergences.csv`, `divergence.json`: pairing, exact selection counts and criteria.
- `results/full/evaluation/clusters/findings.md`, `cluster_profiles.csv`, `cluster_categories.csv`, `cluster_assignments.csv`, `clustering.json`, `clusters.png`, `selection.png`: clustering evidence and plots.
- `results/full/evaluation/replay.png`, `pedestrian_replay.png`, `pedestrian_replay.gif`, `demo_scenario.json`: road/telemetry replay and actual pedestrian divergence demo.
- `results/full/training/training.json`, `parity_features.csv`, `cpp_predictions.csv`: training provenance, validation errors and C++ parity.
- `results/full/hybrid_design.json`: frozen validation evidence and controller hash, written before held-out execution.
- `data/generated/full/`: 1,200 training / 400 validation / 10,000 evaluation scenarios and manifests.
- `models/full/controller.forest`, `controller.joblib`: actual trained C++ model and Python artifact.
- `build-x64/python-tests.xml`, `build-x64/Testing/Temporary/LastTest.log`: automated test records.

## Reproduction on this workspace

```powershell
& "$env:ProgramFiles\CMake\bin\cmake.exe" --build --preset release-x64 --parallel
& "$env:ProgramFiles\CMake\bin\ctest.exe" --preset release-x64
.\.venv\Scripts\python.exe -m pytest tests\python -q
.\scripts\run_pipeline.ps1 -Mode Full -BuildDirectory build-x64 -SkipBuild
```

The installed CMake directory may require a new terminal for PATH discovery; the explicit commands above avoid that requirement. No further tools need installation for the verified x64 workflow. For a new PC, follow `windows_setup.md`. No clean-machine reinstall or native ARM64 build is claimed.

## Accurate résumé bullets

- Built a modular C++20 driving behavior simulator and evaluated rule-based, random-forest, and hybrid controllers across 10,000 held-out synthetic scenarios (30,000 runs).
- Trained a 32-tree acceleration model on 48,156 synthetic teacher demonstrations, verified C++/Python inference parity, and analyzed 9,243 unique behavioral divergences using K-Means and DBSCAN.
- Evaluated interpretable TTC and relative-speed rules that reduced simulated collisions by 11.95% versus the baseline, while documenting an 8.41% increase in hard-braking events and lower route completion.

## Remaining limitations

The dynamics use a longitudinal integrator and lateral servo rather than a bicycle/tire model. No steering actuator, real sensors, noisy perception, road-friction variation, reactive traffic, curved route graph, or learned lane policy is included. Commanded jerk is constrained but stop/speed saturation introduces effective jerk discontinuities. Boxes remain axis-aligned; surrounding trajectories are scripted. Clustering is descriptive; validation cases do not establish causal rule extraction. Synthetic collision rates are deliberately challenging and must not be interpreted as road deployment rates. A separate holdout is required before tuning future revisions. See the interview guide for concrete extensions and tradeoffs.
