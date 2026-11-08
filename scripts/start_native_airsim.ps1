param([int]$Width = 1280, [int]$Height = 720,[switch]$Offscreen,[switch]$Packaged)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$engine = 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$project = Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject'
$settings = Join-Path $root 'configs\airsim-native-settings.json'
$packagedExe=Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged\Windows\SKYFORGE.exe'
if ($Packaged -and !(Test-Path -LiteralPath $packagedExe)) { throw 'Complete package_native_airsim.ps1 first' }
if (!(Test-Path -LiteralPath $engine) -or !(Test-Path -LiteralPath $project)) {
    throw 'Build the native Unreal project before launching it.'
}
$existing = Get-NetTCPConnection -LocalPort 41461 -State Listen -ErrorAction SilentlyContinue
if ($existing) { Write-Output "Native AirSim already listening on 41461 (PID $($existing.OwningProcess))"; exit 0 }
# Close only the known project-owned scenic preview to free its GPU memory.
if (!$Offscreen) { Get-CimInstance Win32_Process -Filter "Name = 'Coastline.exe'" | ForEach-Object {
    if ($_.ExecutablePath -and $_.ExecutablePath.StartsWith((Join-Path $root 'runtime\airsim\Coastline\'), [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    }
} }
[Environment]::SetEnvironmentVariable('UE-LocalDataCachePath',(Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealCache'),'Process')
$log = Join-Path $root 'artifacts\native-airsim.log'
$arguments = @(('"' + $project + '"'), '/Game/SKYFORGE/CoastalRescue', '-game', '-windowed', "-ResX=$Width", "-ResY=$Height", '-dx11', '-nosplash', ('-settings="' + $settings + '"'), ('-abslog="' + $log + '"'))
if ($Packaged) {
    $engine=$packagedExe
    $arguments=@('/Game/SKYFORGE/CoastalRescue','-windowed',"-ResX=$Width","-ResY=$Height",'-dx11','-nosplash',('-settings="'+$settings+'"'),('-abslog="'+$log+'"'))
}
# This is the interactive simulator the user explicitly requested to see.
if ($Offscreen) {
    $arguments += '-RenderOffscreen'
    $process = Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
} else {
    $process = Start-Process -FilePath $engine -ArgumentList $arguments -WorkingDirectory $root -PassThru
}
Write-Output "Started native SKYFORGE AirSim PID $($process.Id); API 127.0.0.1:41461; log $log"
