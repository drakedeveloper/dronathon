$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$editor='D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$project=Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject'
$script=Join-Path $root 'scripts\build_unreal_scene.py'
$log=Join-Path $root 'artifacts\unreal-scene.log'
$cache=Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealCache'
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',$cache,'Process')
& $editor $project -run=pythonscript "-script=$script" -unattended -nullrhi -nosplash -nosound "-abslog=$log" -stdout -FullStdOutLogOutput
if($LASTEXITCODE -ne 0){throw "Unreal scene authoring failed; see $log"}
