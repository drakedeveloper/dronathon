$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$folder=Join-Path $root 'runtime\unreal-deps'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$archive=Join-Path $folder 'AirSim_plugin_Windows_58_350.zip'
$source='https://github.com/Cosys-Lab/Cosys-AirSim/releases/download/5.8-v3.5.0/AirSim_plugin_Windows_58_350.zip'
$expected='4d7cb22241071c0581a33eaf0b9af68f51e222e89092815bbc3cc8f37d8ecffb'
if (!(Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -ne 739940526) {
    & curl.exe --fail --location --silent --show-error --retry 3 --continue-at - --output $archive $source
    if($LASTEXITCODE -ne 0){throw 'Cosys-AirSim plugin download failed; rerun to resume'}
}
$actual=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if($actual -ne $expected){throw 'Cosys-AirSim upstream SHA256 mismatch'}
Write-Host 'Verified Cosys-AirSim v3.5.0 plugin archive against upstream SHA256'
& (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'scripts\prepare_unreal_project.py') $archive
if($LASTEXITCODE -ne 0){throw 'Unreal project preparation failed'}
