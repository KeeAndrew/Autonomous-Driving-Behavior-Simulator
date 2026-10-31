# Small reproducibility fixtures

`examples.csv` contains one deterministic scenario per generator stratum, seed 77. Its manifest records its hash and distribution. Use it for fast manual replay without generating a large dataset.

`regressions.csv` and `regressions.json` capture real validation divergences after experiments run. Cases are selected by collision mismatch and acceleration disagreement within each scenario kind, then baseline/hybrid outcomes are snapshotted. Tests read these expectations; they never update them automatically. Source hashes and per-case reasons are retained in the JSON provenance.

To explicitly capture a new regression suite after reviewing validation changes:

```powershell
.\.venv\Scripts\python.exe -m python.analysis.capture_regressions --scenarios data\generated\full\validation.csv --paired results\full\validation\paired.csv --exe build-x64\Release\simulator.exe --out data\sample_scenarios\regressions.csv
```

Changing regression expectations requires review. A fixed synthetic fixture detects software behavior changes, not proof of physical validity or safety.