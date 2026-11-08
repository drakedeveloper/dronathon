$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$source=[IO.Path]::GetFullPath((Join-Path $root 'runtime\unreal\SKYFORGE\Intermediate'))
$cacheBase=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SKYFORGE\UnrealBuildCache'))
$destination=[IO.Path]::GetFullPath((Join-Path $cacheBase 'ProjectIntermediate'))
if (!$source.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or !$destination.StartsWith($cacheBase+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Resolved cache paths escaped their task directories'
}
if (!(Test-Path -LiteralPath $source)) { throw 'Project intermediate cache is absent' }
$item=Get-Item -LiteralPath $source
if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { Write-Output 'Build cache is already relocated'; exit 0 }
if (Test-Path -LiteralPath $destination) { throw 'Destination exists; refusing to overwrite it' }
$active=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*SKYFORGE.uproject*' }
if ($active) { throw 'Close the task native Unreal project before relocating its cache' }
New-Item -ItemType Directory -Force -Path $cacheBase | Out-Null
Write-Output "Verified build-cache move: $source -> $destination"
Move-Item -LiteralPath $source -Destination $destination
try { New-Item -ItemType Junction -Path $source -Target $destination | Out-Null }
catch { Move-Item -LiteralPath $destination -Destination $source; throw }
Write-Output 'Build cache relocated; existing D: project paths preserved through junction'
