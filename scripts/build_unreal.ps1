param([switch]$Rebuild)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$project=Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject'
$engine='D:\Epic Games\UE_5.8'
if(!(Test-Path -LiteralPath $project)){throw 'Prepare the Unreal project first'}
$cache=Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealCache'
New-Item -ItemType Directory -Force -Path $cache | Out-Null
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',$cache,'Process')
& (Join-Path $root '.venv\Scripts\python.exe') -m scripts.apply_unreal_airframe
if($LASTEXITCODE -ne 0){throw 'Reference airframe generation failed'}
$log=Join-Path $root 'artifacts\unreal-build.log'
$buildArguments=@('SKYFORGEEditor','Win64','Development',"-Project=$project",'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions=1','-NoUBA','-NoXGE','-NoFASTBuild')
if($Rebuild){$buildArguments+='-Rebuild'}
& "$engine\Engine\Build\BatchFiles\Build.bat" @buildArguments 2>&1 |
    Tee-Object -FilePath $log
if($LASTEXITCODE -ne 0){throw "Unreal source build failed; see $log"}
