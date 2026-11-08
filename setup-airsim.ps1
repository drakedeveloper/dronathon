param([switch]$Extract)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath($PSScriptRoot)
$assetRoot = Join-Path $workspace 'runtime\airsim'
New-Item -ItemType Directory -Force -Path $assetRoot | Out-Null
$archive = Join-Path $assetRoot 'Coastline-v1.8.1-windows.zip'
$source = 'https://github.com/microsoft/AirSim/releases/download/v1.8.1-windows/Coastline.zip'
$expectedBytes = 926675941
if (!(Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -ne $expectedBytes) {
    & curl.exe --fail --location --retry 3 --continue-at - --output $archive $source
    if ($LASTEXITCODE -ne 0) { throw 'AirSim download failed; rerun to resume.' }
}
if ((Get-Item -LiteralPath $archive).Length -ne $expectedBytes) { throw 'Unexpected archive length' }
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
@{ source=$source; bytes=$expectedBytes; sha256=$hash; note='Local content hash; upstream release does not supply a signed checksum.' } |
    ConvertTo-Json | Set-Content -Encoding ascii (Join-Path $assetRoot 'download-manifest.json')
Write-Host "AirSim Coastline downloaded on D:; SHA256 $hash"
if ($Extract) {
    & (Join-Path $workspace '.venv\Scripts\python.exe') (Join-Path $workspace 'scripts\extract_airsim.py') $archive
    if ($LASTEXITCODE -ne 0) { throw 'Archive inspection/extraction failed' }
}
