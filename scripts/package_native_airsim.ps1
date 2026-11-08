param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$project=Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject'
$engine='D:\Epic Games\UE_5.8'
$output=Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged'
$staging=Join-Path $env:LOCALAPPDATA 'SKYFORGE\Staging'
if (!(Test-Path -LiteralPath $project)) { throw 'Prepare and author the native project first' }
$gameConfig=Join-Path (Split-Path -Parent $project) 'Config\DefaultGame.ini'
@'
[/Script/EngineSettings.GeneralProjectSettings]
ProjectName=SKYFORGE
ProjectVersion=0.1.0
Description=Autonomous humanitarian coastal rescue research simulator

[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysCook=(Path="/AirSim/Blueprints")
+DirectoriesToAlwaysCook=(Path="/AirSim/Weather")
+DirectoriesToAlwaysCook=(Path="/Game/SKYFORGE")
'@ | Set-Content -LiteralPath $gameConfig -Encoding ascii
New-Item -ItemType Directory -Force -Path $output,$staging | Out-Null
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',(Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealCache'),'Process')
$arguments=@('BuildCookRun',"-project=$project",'-noP4','-platform=Win64','-clientconfig=Development',
    '-cook','-map=/Game/SKYFORGE/CoastalRescue','-stage','-pak','-archive',
    "-archivedirectory=$output","-stagingdirectory=$staging",'-utf8output','-unattended',
    '-nocompileeditor','-UbtArgs="-NoUBA -NoXGE -MaxParallelActions=1"')
if ($SkipBuild) { $arguments+='-skipbuild' } else { $arguments+='-build' }
& "$engine\Engine\Build\BatchFiles\RunUAT.bat" @arguments 2>&1 | Tee-Object -FilePath (Join-Path $root 'artifacts\native-package.log')
if ($LASTEXITCODE -ne 0) { throw 'Native packaging failed; inspect artifacts/native-package.log' }
Write-Output "Packaged simulator: $output"
