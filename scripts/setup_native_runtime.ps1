$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$environment=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-native'
$python=Join-Path $environment 'Scripts\python.exe'
if(!(Test-Path -LiteralPath $python)) {
    & py -3.13 -m venv $environment
    if($LASTEXITCODE -ne 0){throw 'Native GPU environment creation failed'}
}
& $python -m pip install --no-cache-dir --disable-pip-version-check -r (Join-Path $root 'requirements-native.in')
if($LASTEXITCODE -ne 0){throw 'Native GPU runtime installation failed'}
& $python -m pip freeze | Set-Content -Encoding ascii (Join-Path $root 'artifacts\native-requirements.lock.txt')
Write-Host "Native GPU runtime ready: $python"
