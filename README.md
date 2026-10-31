# Autonomous Driving Behavior Simulator

This is a personal project where I'm exploring how different driving controllers handle the same situations. The goal is to get more hands-on experience with C++, machine learning, and the testing involved in autonomous driving software.

This simulator uses a simple 2D road with vehicles, pedestrians, and obstacles. It runs scenarios like following a slower car, reacting to sudden braking, stopping for a pedestrian, and deciding whether there's enough room to change lanes. I compare three controllers to see how their decisions affect collisions, braking, comfort, and progress. 

## How it works

The simulation runs in C++20. Python handles model training, analysis, and visualization.

- **Baseline:** explicit rules for target speed, following distance, braking, and lane changes.
- **ML controller:** a random forest trained to predict acceleration from demonstrations produced by a separate teacher controller. It uses the baseline's lane-change rules.
- **Hybrid controller:** explicit rules that add relative-speed following distances, time-to-collision checks, and pedestrian stopping-distance logic.

Each controller starts with the same scenario conditions. The simulator records what happens, then Python compares the runs and uses K-Means and DBSCAN to group cases where baseline and ML behavior differ. There's also an animated replay to inspect individual scenarios.

The training data is synthetic and comes from the teacher controller. The model is learning to imitate that controller; it isn't trained on real driving footage or production vehicle data.

## What I found

The full experiment ran **10,000 held-out scenarios per controller**, or **30,000 runs** in total. It identified **9,243 scenarios** with meaningful differences between baseline and ML behavior.

| Controller | Collisions | Hard-braking events | Route completion |
|---|---:|---:|---:|
| Baseline | 2,997 | 8,192 | 62.72% |
| ML | 3,000 | 4,100 | 51.38% |
| Hybrid | 2,639 | 8,881 | 58.98% |

There are tradeoffs here. The hybrid had **11.95% fewer collisions** than baseline, but **8.41% more hard-braking events** and lower route completion. The ML controller braked hard less often, but didn't improve the collision count and completed fewer routes.

These results are a useful part of the project: a controller can improve one metric while getting worse on another. The [full results](docs/verified_results.md) include the experiment details and confidence intervals.

## Running it on Windows

You can use the PowerShell terminal inside VS Code. You'll need Visual Studio C++ Build Tools with a Windows SDK, CMake, and Python 3.12. See [Windows setup](docs/windows_setup.md) if you're setting this up on a new computer.

From the project folder, create the Python environment once:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run the smaller experiment:

```powershell
.\scripts\run_pipeline.ps1 -Mode Smoke
```

This builds the simulator, runs the tests, trains the model, and evaluates 160 scenarios per controller. It also creates reports, plots, and replay data. You don't need to activate the Python environment separately.

For the full 10,000-scenario experiment:

```powershell
.\scripts\run_pipeline.ps1 -Mode Full
```

If PowerShell blocks the script, this invocation applies the execution-policy setting only to the new process:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pipeline.ps1 -Mode Smoke
```

Smoke results are written to `results\smoke\evaluation\`; full results go to `results\full\evaluation\`. Open `report.md` for the numbers or `comparison.png` for the plots.

To watch a smoke scenario after running the pipeline:

```powershell
.\.venv\Scripts\python.exe -m python.visualization.replay --telemetry results\smoke\evaluation\baseline_telemetry.csv results\smoke\evaluation\ml_telemetry.csv results\smoke\evaluation\hybrid_telemetry.csv --id 200000
```

The tested build targets Windows x64 and also runs on Windows ARM64 through emulation. Native ARM64 presets are included, but haven't been verified. Generated datasets, models, build files, and reports are kept out of Git.

## Project layout

- `src/` and `include/`: C++ simulation, controllers, scenarios, and metrics.
- `python/`: training, behavioral analysis, and replay.
- `tests/`: C++ and Python tests, including fixed cases from actual validation divergences.
- `scripts/`: the PowerShell pipeline.
- `docs/`: setup instructions and technical explanations.

## Limitations and next steps

This is a simplified simulator on a straight, two-lane road. Traffic follows scripted behavior, visible actors have perfect measurements, and the vehicle model doesn't include tire forces or realistic steering. The results describe this simulation, not how a real autonomous car would perform.

Next steps would be adding noisy perception, more realistic vehicle dynamics, reactive traffic, and stronger rule-based baselines to compare against.

For more detail: [individual commands](docs/workflows.md), [architecture](docs/architecture.md), [vehicle model](docs/simulation_model.md), [controller design](docs/controller_design.md), [ML training](docs/ml_pipeline.md), and [evaluation methodology](docs/evaluation_methodology.md).
