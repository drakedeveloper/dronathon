$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',(Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealCache'),'Process')
$editor='D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
& $editor (Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject') -run=pythonscript "-script=$(Join-Path $PSScriptRoot 'optimize_unreal_meshes.py')" -unattended -nullrhi -nosplash -nosound "-abslog=$(Join-Path $root 'artifacts\unreal-lods.log')" -stdout
if ($LASTEXITCODE -ne 0) { throw 'Mesh optimization failed; inspect artifacts/unreal-lods.log' }
