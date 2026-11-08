$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$python=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native\Scripts\python.exe'
$listener=Get-NetTCPConnection -LocalPort 41461 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    & $python -c "from skyforge.airsim_rpc import AirSimRPC; import numpy as np; r=AirSimRPC(port=41461); s=r.call('getMultirotorState','SKYFORGE'); assert s['landed_state']==0 and np.linalg.norm(list(s['kinematics_estimated']['linear_velocity'].values()))<.2,'The drone is airborne: wait for landing before stopping';r.close()"
    if ($LASTEXITCODE -ne 0) { throw 'Stop refused while the aircraft is moving or airborne' }
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $packageRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged\'))
    if (!$process.ExecutablePath.StartsWith($packageRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected simulator owner; stop it manually' }
    Stop-Process -Id $process.ProcessId
}
$owned=Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -and
    $_.CommandLine.Contains($python) -and $_.CommandLine -match '-m scripts.run_native_mission'
}
$parents=$owned | Where-Object {$_.ParentProcessId -notin $owned.ProcessId}
foreach ($process in $parents) { & taskkill /PID $process.ProcessId /T /F | Out-Null }
Write-Output 'Stopped the grounded SKYFORGE simulator and mission services.'
