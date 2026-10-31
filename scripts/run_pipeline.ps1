[CmdletBinding()]
param(
    [ValidateSet('Smoke','Full')][string]$Mode='Smoke',
    [string]$BuildDirectory='build-x64',
    [switch]$SkipBuild,
    [string]$Generator='',
    [string]$Architecture=''
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Root=Split-Path -Parent $PSScriptRoot
function Invoke-Checked {
    param([string]$Program,[string[]]$Arguments)
    Write-Host ('> '+$Program+' '+($Arguments -join ' '))
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
Push-Location -LiteralPath $Root
try {
    $Python=Join-Path $Root '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $Python)) { throw 'Create .venv and install requirements.txt first; see docs\windows_setup.md.' }
    $CMake='cmake'
    if (!(Get-Command cmake -ErrorAction SilentlyContinue)) {
        $CMake=Join-Path $env:ProgramFiles 'CMake\bin\cmake.exe'
        if (!(Test-Path -LiteralPath $CMake)) { throw 'CMake is missing; see docs\windows_setup.md.' }
    }
    if (!$SkipBuild) {
        if (!$Generator) {
            $VsWhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
            if (!(Test-Path -LiteralPath $VsWhere)) { throw 'Visual Studio not detected; supply -Generator explicitly.' }
            $Version=& $VsWhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationVersion
            if (!$Version) { throw 'Install Desktop development with C++ and Windows SDK.' }
            $Major=[int]($Version.Split('.')[0])
            if ($Major -eq 17) { $Generator='Visual Studio 17 2022' }
            elseif ($Major -eq 18) { $Generator='Visual Studio 18 2026' }
            else { throw 'Unrecognized Visual Studio; supply -Generator explicitly.' }
        }
        if (!$Architecture) {
            if ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -eq 'Arm64') {
                $ArmLib=Get-ChildItem -Path (Join-Path (& $VsWhere -latest -products '*' -property installationPath) 'VC\Tools\MSVC\*\lib\arm64') -ErrorAction SilentlyContinue
                if ($ArmLib) { $Architecture='ARM64' } else { $Architecture='x64'; Write-Host 'ARM64 target libraries absent; using installed Windows x64 target.' }
            } else { $Architecture='x64' }
        }
        Invoke-Checked $CMake @('-S','.','-B',$BuildDirectory,'-G',$Generator,'-A',$Architecture,'-DBUILD_TESTING=ON')
        Invoke-Checked $CMake @('--build',$BuildDirectory,'--config','Release','--parallel')
    }
    $CTest=Join-Path (Split-Path (Get-Command $CMake).Source) 'ctest.exe'
    Invoke-Checked $CTest @('--test-dir',$BuildDirectory,'-C','Release','--output-on-failure')
    $Exe=Join-Path $Root (Join-Path $BuildDirectory 'Release\simulator.exe')
    if (!(Test-Path -LiteralPath $Exe)) { $Exe=Join-Path $Root (Join-Path $BuildDirectory 'simulator.exe') }
    $env:SIM_EXE=$Exe
    Invoke-Checked $Python @('-m','pytest','tests\python','-q','--junitxml',"$BuildDirectory\python-tests.xml")
    $Tag=$Mode.ToLowerInvariant()
    $Data="data/generated/$Tag"; $Result="results/$Tag"; $Model="models/$Tag/controller.forest"
    New-Item -ItemType Directory -Force -Path $Data,$Result,(Split-Path $Model) | Out-Null
    if ($Mode -eq 'Full') { $TrainCount=1200; $ValCount=400; $EvalCount=10000 } else { $TrainCount=120; $ValCount=40; $EvalCount=160 }
    foreach ($Split in @(@('train',1001,0,$TrainCount),@('validation',2001,100000,$ValCount),@('evaluation',3001,200000,$EvalCount))) {
        Invoke-Checked $Python @('-m','python.training.generate','--out',"$Data/$($Split[0]).csv",'--seed',"$($Split[1])",'--id-offset',"$($Split[2])",'--count',"$($Split[3])")
    }
    foreach ($Split in @('train','validation')) {
        Invoke-Checked $Exe @('--scenarios',"$Data/$Split.csv",'--controller','teacher','--metrics',"$Result/${Split}_teacher_metrics.csv",'--telemetry',"$Result/${Split}_teacher.csv",'--sample-every','5')
    }
    Invoke-Checked $Python @('-m','python.training.train','--train',"$Result/train_teacher.csv",'--validation',"$Result/validation_teacher.csv",'--model',$Model,'--out',"$Result/training",'--exe',$Exe)
    foreach ($Controller in @('baseline','ml')) {
        $Arguments=@('--scenarios',"$Data/validation.csv",'--controller',$Controller,'--metrics',"$Result/validation/${Controller}_metrics.csv",'--telemetry',"$Result/validation/${Controller}_telemetry.csv",'--sample-every','10')
        if ($Controller -eq 'ml') { $Arguments+=@('--model',$Model) }
        Invoke-Checked $Exe $Arguments
    }
    Invoke-Checked $Python @('-m','python.analysis.divergence','--baseline',"$Result/validation/baseline_metrics.csv",'--ml',"$Result/validation/ml_metrics.csv",'--baseline-telemetry',"$Result/validation/baseline_telemetry.csv",'--ml-telemetry',"$Result/validation/ml_telemetry.csv",'--out',"$Result/validation")
    Invoke-Checked $Python @('-m','python.analysis.cluster','--input',"$Result/validation/divergences.csv",'--out',"$Result/validation/clusters")
    Invoke-Checked $Python @('-m','python.analysis.freeze','--paired',"$Result/validation/paired.csv",'--out',"$Result/hybrid_design.json")
    foreach ($Controller in @('baseline','ml','hybrid')) {
        $Arguments=@('--scenarios',"$Data/evaluation.csv",'--controller',$Controller,'--metrics',"$Result/evaluation/${Controller}_metrics.csv",'--telemetry',"$Result/evaluation/${Controller}_telemetry.csv",'--sample-every','10')
        if ($Controller -eq 'ml') { $Arguments+=@('--model',$Model) }
        Invoke-Checked $Exe $Arguments
    }
    Invoke-Checked $Python @('-m','python.analysis.divergence','--baseline',"$Result/evaluation/baseline_metrics.csv",'--ml',"$Result/evaluation/ml_metrics.csv",'--baseline-telemetry',"$Result/evaluation/baseline_telemetry.csv",'--ml-telemetry',"$Result/evaluation/ml_telemetry.csv",'--out',"$Result/evaluation")
    Invoke-Checked $Python @('-m','python.analysis.cluster','--input',"$Result/evaluation/divergences.csv",'--out',"$Result/evaluation/clusters")
    Invoke-Checked $Python @('-m','python.analysis.report','--baseline',"$Result/evaluation/baseline_metrics.csv",'--ml',"$Result/evaluation/ml_metrics.csv",'--hybrid',"$Result/evaluation/hybrid_metrics.csv",'--out',"$Result/evaluation")
    Invoke-Checked $Python @('-m','python.visualization.replay','--telemetry',"$Result/evaluation/baseline_telemetry.csv", "$Result/evaluation/ml_telemetry.csv", "$Result/evaluation/hybrid_telemetry.csv",'--id','200000','--out',"$Result/evaluation/replay.png")
    & $Python -m pip freeze --local | Set-Content -Encoding UTF8 "$Result/requirements-lock.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Failed to capture dependency lock' }
    Write-Host "Completed $Mode pipeline: $EvalCount held-out scenarios per controller. Read $Result/evaluation/report.md"
} catch {
    Write-Error $_
    exit 1
} finally { Pop-Location }