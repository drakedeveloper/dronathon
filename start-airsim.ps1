param([ValidateSet('Laptop','Home')][string]$Profile='Laptop')
$ErrorActionPreference='Stop'
$scene=Join-Path $PSScriptRoot 'runtime\airsim\Coastline'
$launcher=Join-Path $scene 'Coastline\WindowsNoEditor\Coastline.exe'
if (!(Test-Path -LiteralPath $launcher)) { throw 'Run setup-airsim.ps1 -Extract first.' }
$settings=Join-Path $PSScriptRoot 'sim\airsim-settings.json'
$resolution=if ($Profile -eq 'Home') { '-ResX=1920 -ResY=1080' } else { '-ResX=1280 -ResY=720' }
$arguments='-windowed '+$resolution+' -settings="'+$settings+'"'
# This is the interactive simulation window the user asked to inspect.
Start-Process -FilePath $launcher -WorkingDirectory (Split-Path -Parent $launcher) -ArgumentList $arguments -WindowStyle Normal
