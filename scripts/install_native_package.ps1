param([Parameter(Mandatory=$true)][string]$Archive)
$ErrorActionPreference='Stop'
$resolved=(Resolve-Path -LiteralPath $Archive).Path
$expected='c9b982aa7b1fa83a3443aa0834d1c06b611472867e01bd5fafbbde537b2942fe'
if ((Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Native package checksum mismatch' }
$destination=Join-Path $env:LOCALAPPDATA 'SKYFORGE\Packaged'
if (Test-Path -LiteralPath (Join-Path $destination 'Windows\SKYFORGE.exe')) { throw 'Package already installed; use start-skyforge.ps1' }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Expand-Archive -LiteralPath $resolved -DestinationPath $destination
Write-Output "Verified native scene installed at $destination"
