$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$python=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native\Scripts\python.exe'
$owned=Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -and
    $_.CommandLine.Contains($python) -and $_.CommandLine -match '-m scripts.run_native_mission'
}
$parents=$owned | Where-Object {$_.ParentProcessId -notin $owned.ProcessId}
$listener=Get-NetTCPConnection -LocalPort 41461 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $packageRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged\'))
    if (!$process.ExecutablePath -or !$process.ExecutablePath.StartsWith($packageRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected simulator owner; stop it manually' }
    foreach ($parent in $parents) {
        Set-Content -LiteralPath (Join-Path $root 'artifacts\native\stop-request.txt') -Value ([string]$parent.ProcessId) -Encoding ascii
    }
    Write-Output 'Stopping SKYFORGE: waiting for verified landing before closing AirSim. Keep this window open.'
    & $python -c "import time,numpy as np; from skyforge.airsim_rpc import AirSimRPC
deadline=time.monotonic()+180
with AirSimRPC(port=41461) as r:
 while time.monotonic()<deadline:
  s=r.call('getMultirotorState','SKYFORGE')
  if s['landed_state']==0 and np.linalg.norm(list(s['kinematics_estimated']['linear_velocity'].values()))<.2:break
  time.sleep(.5)
 else:raise SystemExit('Landing has not completed. AirSim was left running; check the dashboard before retrying.')
print('Landing confirmed.')"
    if ($LASTEXITCODE -ne 0) { throw 'AirSim remains open because landing could not be confirmed.' }
    # Allow the owner to finish its recovery/disarm sequence before closing RPC.
    foreach ($parent in $parents) { Wait-Process -Id $parent.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
    Stop-Process -Id $process.ProcessId
}
foreach ($process in $parents) {
    if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) { & taskkill /PID $process.ProcessId /T /F | Out-Null }
}
Write-Output 'Stopped the grounded SKYFORGE simulator and mission services.'
