$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
& (Join-Path $root 'scripts\stop_skyforge.ps1')
$launcher=Join-Path $root 'runtime\airsim\Coastline\Coastline\WindowsNoEditor\Coastline.exe'
if (!(Test-Path -LiteralPath $launcher)) { throw 'The separately installed Coastline environment is absent. Use START-QUALITY-DEMO.bat for the rescue world.' }
$settings=Get-Content -LiteralPath (Join-Path $root 'sim\airsim-settings.json') -Raw | ConvertFrom-Json
$settings.ViewMode='Fpv'
$settings | Add-Member -NotePropertyName PhysicsEngineName -NotePropertyValue ExternalPhysicsEngine -Force
$settingsPath=Join-Path $root 'runtime\airsim\scenic-settings.json'
$settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsPath -Encoding ascii
$existing=Get-NetTCPConnection -LocalPort 41451 -State Listen -ErrorAction SilentlyContinue
if (!$existing) {
    $arguments=@('-windowed','-ResX=1600','-ResY=900',('-settings="'+$settingsPath+'"'),'-ExecCmds="t.MaxFPS 30,r.Streaming.PoolSize 1200,r.MaxAnisotropy 8,r.MotionBlurQuality 0"')
    Start-Process -FilePath $launcher -WorkingDirectory (Split-Path -Parent $launcher) -ArgumentList $arguments -WindowStyle Normal
}
Write-Output 'Coastline cinematic spectator preview. This is separate from the rescue flight demonstration.'
$python=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native\Scripts\python.exe'
& $python -m scripts.airsim_scenic
if ($LASTEXITCODE -ne 0) { throw 'Scenic camera setup failed; the validated rescue launcher is unchanged.' }
