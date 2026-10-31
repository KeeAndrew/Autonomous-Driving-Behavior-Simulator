# Individual workflow commands

The following commands run from the repository root after setup. They use the verified x64 build and `Full` experiment artifact locations; substitute `smoke` paths when appropriate. The pipeline executes them in dependency order.

```powershell
# 1. Build
cmake --preset vs2022-x64
cmake --build --preset release-x64 --parallel
# 2. C++ tests
ctest --preset release-x64
# 3. Python tests
.\.venv\Scripts\python.exe -m pytest tests\python -q
# 4. Generate independent datasets
.\.venv\Scripts\python.exe -m python.training.generate --out data\generated\full\train.csv --count 1200 --seed 1001 --id-offset 0
.\.venv\Scripts\python.exe -m python.training.generate --out data\generated\full\validation.csv --count 400 --seed 2001 --id-offset 100000
.\.venv\Scripts\python.exe -m python.training.generate --out data\generated\full\evaluation.csv --count 10000 --seed 3001 --id-offset 200000
# 5. Generate teacher demonstrations (training and validation only)
.\build-x64\Release\simulator.exe --scenarios data\generated\full\train.csv --controller teacher --metrics results\full\train_teacher_metrics.csv --telemetry results\full\train_teacher.csv --sample-every 5
.\build-x64\Release\simulator.exe --scenarios data\generated\full\validation.csv --controller teacher --metrics results\full\validation_teacher_metrics.csv --telemetry results\full\validation_teacher.csv --sample-every 5
# 6. Train, export, and verify C++ inference
.\.venv\Scripts\python.exe -m python.training.train --train results\full\train_teacher.csv --validation results\full\validation_teacher.csv --model models\full\controller.forest --out results\full\training --exe build-x64\Release\simulator.exe
# 7. Baseline evaluation
.\build-x64\Release\simulator.exe --scenarios data\generated\full\evaluation.csv --controller baseline --metrics results\full\evaluation\baseline_metrics.csv --telemetry results\full\evaluation\baseline_telemetry.csv --sample-every 10
# 8. ML evaluation
.\build-x64\Release\simulator.exe --scenarios data\generated\full\evaluation.csv --controller ml --model models\full\controller.forest --metrics results\full\evaluation\ml_metrics.csv --telemetry results\full\evaluation\ml_telemetry.csv --sample-every 10
# 9. Hybrid evaluation (freeze validation hypotheses before evaluating)
.\build-x64\Release\simulator.exe --scenarios data\generated\full\evaluation.csv --controller hybrid --metrics results\full\evaluation\hybrid_metrics.csv --telemetry results\full\evaluation\hybrid_telemetry.csv --sample-every 10
# 10. Paired divergence analysis
.\.venv\Scripts\python.exe -m python.analysis.divergence --baseline results\full\evaluation\baseline_metrics.csv --ml results\full\evaluation\ml_metrics.csv --baseline-telemetry results\full\evaluation\baseline_telemetry.csv --ml-telemetry results\full\evaluation\ml_telemetry.csv --out results\full\evaluation
# 11. K-Means and DBSCAN
.\.venv\Scripts\python.exe -m python.analysis.cluster --input results\full\evaluation\divergences.csv --out results\full\evaluation\clusters
# 12. Evaluation reports and plots
.\.venv\Scripts\python.exe -m python.analysis.report --baseline results\full\evaluation\baseline_metrics.csv --ml results\full\evaluation\ml_metrics.csv --hybrid results\full\evaluation\hybrid_metrics.csv --out results\full\evaluation
# 13. Interactive replay (one or several controllers); add --out FILE.png or --gif FILE.gif to export
.\.venv\Scripts\python.exe -m python.visualization.replay --telemetry results\full\evaluation\baseline_telemetry.csv results\full\evaluation\ml_telemetry.csv results\full\evaluation\hybrid_telemetry.csv --id 200000
# To capture every timestep of a single scenario, use --id and omit --sample-every:
.\build-x64\Release\simulator.exe --scenarios data\generated\full\evaluation.csv --controller ml --model models\full\controller.forest --metrics results\replay_ml_metrics.csv --telemetry results\replay_ml.csv --id 200000
# 14. Full reproducible workflow, including validation analysis before held-out runs
.\scripts\run_pipeline.ps1 -Mode Full
```

The complete pipeline runs baseline/ML on validation, clusters those divergences, and records `hybrid_design.json` before any held-out runs. The standalone examples above show individual operations; use the complete pipeline for the recorded experiment protocol.

## Outputs

`results\full\evaluation\report.md` and `comparison.csv` contain measured outcomes; `report.json` includes paired bootstrap intervals and input hashes. `divergences.csv` has one row per selected scenario. `clusters\findings.md`, `cluster_profiles.csv`, `cluster_categories.csv`, `clusters.png`, and `selection.png` describe discovered groups. `comparison.png` and `replay.png` illustrate controller outcomes. Model provenance and parity are in `results\full\training\training.json`. Small failure-derived fixtures live in `data\sample_scenarios\`.

