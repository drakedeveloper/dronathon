$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$directory=Join-Path $env:LOCALAPPDATA 'SKYFORGE\venv-training'
$python=Join-Path $directory 'Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) {
    & (Join-Path $root '.venv\Scripts\python.exe') -m venv $directory
    if ($LASTEXITCODE -ne 0) { throw 'Training environment creation failed' }
}
# Official CUDA 12.8 wheels support the RTX 2050; isolated from CUDA 13 ORT.
$wheelDirectory=Join-Path $env:LOCALAPPDATA 'SKYFORGE\wheels'
New-Item -ItemType Directory -Force -Path $wheelDirectory | Out-Null
$wheel=Join-Path $wheelDirectory 'torch-2.7.1+cu128-cp313-cp313-win_amd64.whl'
$expected='500ad5b670483f62d4052e41948a3fb19e8c8de65b99f8d418d879cbb15a82d6'
if (!(Test-Path -LiteralPath $wheel) -or (Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    & curl.exe --fail --location --retry 3 --continue-at - --output $wheel 'https://download.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp313-cp313-win_amd64.whl'
    if ($LASTEXITCODE -ne 0) { throw 'Torch download failed; rerun to resume' }
    if ((Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Torch upstream SHA256 mismatch' }
}
& $python -m pip install --no-cache-dir $wheel torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch install failed' }
& $python -m pip install --no-cache-dir ultralytics==8.4.207 onnx onnxslim opencv-python==4.13.0.92 pyyaml scipy
if ($LASTEXITCODE -ne 0) { throw 'Detector training dependencies failed' }
& $python -c "import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))"
if ($LASTEXITCODE -ne 0) { throw 'Training GPU verification failed' }
& $python -m pip freeze | Set-Content -Encoding ascii (Join-Path $root 'artifacts\native-training-requirements.lock.txt')
