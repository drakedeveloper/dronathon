# This stop action is for the local simulator only, never a real vehicle.
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Set-Location -LiteralPath $root
$python=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native\Scripts\python.exe'
$packageRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged\'))
$project=Join-Path $root 'runtime\unreal\SKYFORGE\SKYFORGE.uproject'
$modules='-m\s+(scripts\.run_native_mission|station\.server|skyforge\.airsim_(mission|controller|scenario))(\s|$)'
$all=Get-CimInstance Win32_Process
$owned=$all | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.ExecutablePath -and $_.ExecutablePath.Equals($python,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match $modules) -or
    ($_.Name -eq 'SKYFORGE.exe' -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($packageRoot,[StringComparison]::OrdinalIgnoreCase)) -or
    ($_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -and $_.CommandLine.Contains($project))
}
foreach ($process in $owned) {
    if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) {
        # A parent tree termination may already have removed this child.
        $savedPreference=$ErrorActionPreference
        $ErrorActionPreference='SilentlyContinue'
        & taskkill /PID $process.ProcessId /T /F 2>$null | Out-Null
        $ErrorActionPreference=$savedPreference
    }
}
# Closing the local simulator deliberately aborts the run; no landing RPC required.
$deadline=(Get-Date).AddSeconds(8)
do {
    $remaining=@($owned | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue })
    if ($remaining.Count -eq 0) { break }
    Start-Sleep -Milliseconds 200
} while ((Get-Date) -lt $deadline)
if ($remaining.Count -gt 0) { throw 'A SKYFORGE process could not be closed. Close its window and retry.' }
Write-Output 'SKYFORGE demo closed. Ready for a fresh start.'
$global:LASTEXITCODE=0
