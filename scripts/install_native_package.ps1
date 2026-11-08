param([Parameter(Mandatory=$true)][string]$Archive)
$ErrorActionPreference='Stop'
$resolved=(Resolve-Path -LiteralPath $Archive).Path
$expected='684cd175167f94816899e2d7d1441a51b1944ed64f8c4f52d93c9d216321f0ce'
if ((Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Native package checksum mismatch' }
$destination=Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged'
if (Test-Path -LiteralPath (Join-Path $destination 'Windows\SKYFORGE.exe')) { throw 'Package already installed; use start-skyforge.ps1' }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Expand-Archive -LiteralPath $resolved -DestinationPath $destination
Write-Output "Verified native scene installed at $destination"
