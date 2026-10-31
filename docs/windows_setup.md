# Native Windows setup

Use the existing repository folder; never clone or initialize a second repository. Commands below are PowerShell 5.1/7 compatible. Paths with spaces must be quoted, and executable paths use the `&` call operator. Source code and scripts contain no user-specific absolute paths.

## Inspect before installing

```powershell
Get-Location
Resolve-Path .
git rev-parse --show-toplevel
git status --short
git remote -v
$PSVersionTable.PSVersion
[Runtime.InteropServices.RuntimeInformation]::OSDescription
[Runtime.InteropServices.RuntimeInformation]::OSArchitecture
Get-Command git,cmake,ninja,cl,py,python,winget -ErrorAction SilentlyContinue
$VsWhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $VsWhere) { & $VsWhere -products '*' -format json }
if (Get-Command py -ErrorAction SilentlyContinue) { py -0p }
```

Do not treat missing `cl` in ordinary PowerShell as evidence of missing Build Tools. A Visual Studio CMake generator discovers the toolchain without manually initializing a developer shell. Native Ninja/MSVC builds require Developer PowerShell or the corresponding Visual Studio developer environment.

## Dependencies and safe installation options

Run installers only with your approval. Already-compatible installations need no reinstall. The commands are optional install instructions, not actions performed by the pipeline.

| Tool | Requirement and official download | Installation and verification |
|---|---|---|
| Git for Windows | Mandatory for repository workflow; [Git](https://git-scm.com/download/win) | Existing clone only. `winget install --id Git.Git --exact`; verify `git --version`, root and remote. |
| Visual Studio / Build Tools | Mandatory C++20 compiler, linker and SDK; [downloads](https://visualstudio.microsoft.com/downloads/) and [MSVC install guide](https://learn.microsoft.com/en-us/cpp/overview/acquire-msvc) | Build Tools is command-line tooling without the full IDE. Full Visual Studio also works. Choose **Desktop development with C++**, compatible MSVC v143, and Windows 10/11 SDK. On ARM64 explicitly add **MSVC v143 ARM64/ARM64EC build tools**. Verify using vswhere, configure/build, and CTest. |
| CMake >=3.24 | Mandatory build generator/CTest; [CMake](https://cmake.org/download/) | `winget install --id Kitware.CMake --exact`; verify `cmake --version` and `cmake --help`. Reopen terminal if PATH did not refresh, or call `& "$env:ProgramFiles\CMake\bin\cmake.exe"`. |
| Python 3.11–3.13, pip, venv | Mandatory training/analysis; [Python Windows](https://www.python.org/downloads/windows/) | Prefer Python 3.12 x64 for compatible wheels on Windows ARM64 through emulation, or native ARM64 if all wheels are available. `winget install --id Python.Python.3.12 --exact --architecture x64`; installer should include pip and launcher. Verify `py -0p`, `py -3.12 --version`, `py -3.12 -m pip --version`. |
| Python packages | Mandatory training/plots/tests; [scikit-learn](https://scikit-learn.org/stable/install.html), [NumPy](https://numpy.org/install/), [pandas](https://pandas.pydata.org/docs/getting_started/install.html), [Matplotlib](https://matplotlib.org/stable/install/index.html), [pytest](https://docs.pytest.org/en/stable/getting-started.html) | Install bounded `requirements.txt` inside `.venv`; the tested x64 Python 3.12 environment is also pinned in `requirements-windows-x64.lock.txt`. Exact versions are saved after each run. No source builds should be needed with x64 Python 3.12 wheels. |
| Ninja | Optional; [Ninja](https://ninja-build.org/) | Not required by VS presets. `winget install --id Ninja-build.Ninja --exact`; verify `ninja --version`. Use only in an initialized MSVC developer environment. |
| Editor | Optional; [VS Code](https://code.visualstudio.com/) | Existing Codex editor is sufficient. C/C++ and Python VS Code extensions can help debugging; no editor installation is required. |
| winget | Optional Windows package manager; [Microsoft installation](https://learn.microsoft.com/en-us/windows/package-manager/winget/) | Usually provided by App Installer. Verify `winget --version`. Use official graphical installers if unavailable. |

For VS 2022 Build Tools with x64 and ARM64 targets:

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override '--wait --quiet --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.VC.Tools.ARM64'
```

If Build Tools is already installed but lacks ARM64, open Visual Studio Installer, select Modify, and add the ARM64 component. The default C++ workload may only install x64/x86 libraries even on ARM64 Windows. A Windows SDK is required for both targets. Do not assume a particular Visual Studio version: `vs2022-*` presets require VS 2022; the separate VS 2026 preset is supplied for compatible newer installations and requires a CMake version that recognizes it.

There are **no C++ third-party downloads**: no FetchContent, no GoogleTest package manager, no JSON/ONNX/Eigen installation. CTest executes the local contract harness. Python wheel dependencies are the only project-level network downloads, and the launcher itself never installs them automatically.

## Python environment

```powershell
# Use an interpreter actually listed by py -0p.
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import sys,numpy,pandas,sklearn,matplotlib,pytest; print(sys.version)"
```

If `py` is missing, use `& 'FULL_PATH_TO_INSTALLED_PYTHON\python.exe' -m venv .venv` with a verified 3.11+ interpreter. Avoid the Microsoft Store alias and outdated 32-bit Python. `Get-Command python -All` and `where.exe python` distinguish installations. Activation is optional. A venv depends on its base interpreter remaining installed; recreate it if that interpreter moves.

## Build/test/run without presets

```powershell
# ARM64 Windows with VS 2022 and ARM64 tools:
cmake -S . -B build -G 'Visual Studio 17 2022' -A ARM64 -DBUILD_TESTING=ON
cmake --build build --config Release --parallel
ctest --test-dir build -C Release --output-on-failure
.\.venv\Scripts\python.exe -m pytest tests\python -q
.\scripts\run_pipeline.ps1 -Mode Smoke -SkipBuild
.\scripts\run_pipeline.ps1 -Mode Full -SkipBuild
```

For x64 target, use `-A x64 -B build-x64`, and set `$env:SIM_EXE=(Join-Path (Get-Location) 'build-x64\Release\simulator.exe')` before Python tests. Run pipeline with `-BuildDirectory build-x64`. Visual Studio is multi-config: `--config Release` selects Release; CMAKE_BUILD_TYPE is not needed. Keep different generator/architecture builds in different directories. The pipeline resolves its root through `$PSScriptRoot`, so it runs from any current directory.

## Troubleshooting

- **`cl.exe` missing:** use the VS generator, or open Developer PowerShell for optional Ninja. Do not edit global compiler environment variables.
- **Generator/SDK not found:** inspect vswhere and Visual Studio Installer; install the matching C++ workload/SDK. ARM64 requires separate target libraries. CMake's `BaseOutputPath/OutputPath` error during VCTargetsPath probing can indicate missing ARM64 components. Use a separate build directory when changing generator/architecture.
- **C++20 errors/linker failures:** use a supported MSVC toolset, verify CMake selects it, and read the first compile/link error. Do not mix ARM64 and x64 libraries or Debug and Release outputs. Built executables live in `build\Release\`, not `build\` for VS.
- **Execution policy:** scripts can be blocked even though direct executable commands work. Review the script and use direct documented CLI commands, or approve a process-scoped invocation `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pipeline.ps1 -Mode Smoke`. No permanent policy change is required or performed.
- **Python/wheels:** check interpreter version and bitness with `.\.venv\Scripts\python.exe -c "import sys,struct; print(sys.version,struct.calcsize('P')*8)"`. A native ARM64 interpreter may lack specific wheels. Use an approved x64 Python 3.12 installation instead of attempting unsupported source builds. Do not install packages into the old Python 3.7 installation.
- **Network restrictions:** configure a permitted Python package mirror or approved offline wheel directory. CMake never fetches dependencies. Preserve package versions/hashes and never silently substitute libraries.
- **Defender/file locks:** close active simulator/replay processes and wait for scans before retrying. Do not disable antivirus globally. Prefer local non-synchronized working directories if scans repeatedly lock compiler files.
- **Path length:** this repository path contains spaces and is moderately long; always quote paths. If dependency/build paths exceed Windows limits, choose shorter relative build directories inside the same root. Changing Windows long-path policy requires user/admin approval.
- **Permissions:** confirm the opened repository is writable; do not create a substitute project elsewhere. A sandbox may need a workspace-access grant even when ordinary File Explorer can access the drive.
- **Separators:** PowerShell examples use Windows paths. CSV/model CLI paths are handled by `std::filesystem`, Python uses pathlib, and the pipeline's relative paths work on native Windows. Do not invoke Bash wrappers.

See `verified_results.md` for actual detected compiler/SDK/Python versions and completed tests; setup instructions are not evidence that an unexecuted configuration passed.