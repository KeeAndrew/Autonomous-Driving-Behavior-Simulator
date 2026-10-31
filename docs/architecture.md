# Architecture

The executable owns deterministic simulation and all controller metrics. Python owns experiment preparation and statistical analysis. Controllers receive only an `Observation`, never the scenario, simulation clock, hidden actors, future actor scripts, or evaluation metrics. The same observation function and actuator constraints serve every controller.

## Data flow

1. Python generates independent CSV scenario sets, evenly allocated across eight strata; each manifest records counts, seed, and SHA-256.
2. C++ validates numeric schema/bounds and executes a teacher controller to gather training/validation demonstrations.
3. Python fits 32 regression trees with depth at most 10 and leaves of at least eight samples. The exporter writes all node indices, thresholds, and predictions.
4. The C++ forest loader validates version, dimensions, finite values, forward-only child topology, and size bounds. Inference reproduces scikit-learn float32 input semantics.
5. Baseline/ML validation trajectories provide behavioral comparisons. The hybrid remains an interpretable predeclared hypothesis; validation evidence is saved before held-out execution.
6. All three controllers run identical held-out scenario rows. Metrics use every timestep; telemetry may be sampled to reduce disk use.
7. Python aligns telemetry, selects actual divergences, clusters standardized vectors, and produces paired bootstrap reports and plots.

`simulation/types.hpp` defines value-semantic data contracts. The engine accepts a per-frame callback, so CSV output remains outside its update logic. Scenario, controller, dynamics, and metric interfaces are separately testable. No pointers own heap memory; model data uses standard containers and RAII streams. `Controller` stores a non-owning forest pointer whose owner in `main` lives longer than every simulation.

The CLI rejects unknown/duplicate flags, invalid scenarios, invalid model files, missing required files, and unmatched IDs. Output parent directories are created through `std::filesystem`; errors return exit code 1. The PowerShell launcher checks each external program's exit status and stops on failure. Reruns deterministically overwrite generated outputs in their mode directory.

## Dependency decisions

GoogleTest, nlohmann/json, Eigen, and ONNX Runtime are unnecessary for this initial model. A local test harness gives actual failing process status even in Release, unlike disabled `assert` statements. Numeric CSV avoids a network fetch at configure time. Scalar models need no linear-algebra library. A bounded text tree format makes prediction latency and portability straightforward, with explicit parity tests; it would be inappropriate for large neural models. Python requires NumPy, pandas, scikit-learn, Matplotlib, and pytest. Seaborn is optional and omitted.

## Extension points

Replace `integrate` with a validated bicycle/actuator model; generalize Actor to multiple dynamic agents; add perception noise/latency; replace the fixed two-lane road with a route graph. A future controller interface could accept a richer scene graph without moving evaluator state into its input. For model changes, increment the feature schema and maintain export/import parity before any experiment.