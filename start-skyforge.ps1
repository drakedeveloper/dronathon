param([ValidateSet('Native','Gazebo')][string]$Backend='Native',[switch]$Editor,[switch]$ExitOnComplete,[ValidateRange(1,59.2)][double]$EnergyWh=20,[switch]$Realtime,[switch]$Reset,[switch]$Observer,[ValidateSet('Default','Balanced')][string]$VisualQuality='Default')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($PSScriptRoot)
Set-Location -LiteralPath $root
if ($Backend -eq 'Gazebo') { & (Join-Path $root 'start-mission.ps1') -Gui; exit $LASTEXITCODE }
$python=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Run scripts/setup_native_runtime.ps1 first' }
$models=Join-Path $root 'models\native'
if (!(Test-Path -LiteralPath (Join-Path $models 'secondary.onnx'))) { throw 'Native models absent; restore models/native from the repository' }
& (Join-Path $root 'scripts\stop_skyforge.ps1')
if (Get-NetTCPConnection -LocalPort 8768 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8768 is occupied by another application; SKYFORGE did not close unrelated programs.' }
if ($Editor) { & (Join-Path $root 'scripts\start_native_airsim.ps1') -VisualQuality $VisualQuality }
else { & (Join-Path $root 'scripts\start_native_airsim.ps1') -Packaged -Realtime:$Realtime -Offscreen:$Realtime -VisualQuality $VisualQuality }
if ($LASTEXITCODE -ne 0) { throw 'Simulator launch failed' }
& $python -c "import time; from skyforge.airsim_rpc import AirSimRPC; deadline=time.monotonic()+90; ready=False
while time.monotonic()<deadline:
 try:
  with AirSimRPC(port=41461,timeout=2) as rpc:
   if rpc.call('ping'):ready=True;break
 except OSError:pass
 time.sleep(.5)
assert ready,'Simulator API startup timed out'"
if ($LASTEXITCODE -ne 0) { throw 'Simulator API did not become ready' }
if ($Reset) {
    & $python -c "from skyforge.airsim_rpc import AirSimRPC; import numpy as np; r=AirSimRPC(port=41461); s=r.call('getMultirotorState','SKYFORGE'); v=s['kinematics_estimated']['linear_velocity']; assert s['landed_state']==0 and np.linalg.norm(list(v.values()))<.15,'Reset requires a stationary landed drone'; r.call('reset');r.close()"
    if ($LASTEXITCODE -ne 0) { throw 'Grounded reset refused' }
}
$arguments=@('-m','scripts.run_native_mission','--device','cuda','--models',$models,'--person-confidence','.25','--render-fps','75','--energy-wh',([string]$EnergyWh))
if ($VisualQuality -eq 'Balanced') { $arguments[$arguments.IndexOf('--render-fps')+1]='60' }
if ($Observer) { $arguments+='--observer' }
if ($ExitOnComplete) { $arguments+='--exit-on-complete' }
Write-Output 'SKYFORGE station: http://127.0.0.1:8768'
& $python @arguments
exit $LASTEXITCODE
