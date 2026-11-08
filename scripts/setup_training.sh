set -eo pipefail
python3 -m venv /opt/skyforge/training-venv
/opt/skyforge/training-venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check torch torchvision --index-url https://download.pytorch.org/whl/cpu
/opt/skyforge/training-venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check ultralytics==8.4.207 onnx onnxslim pyyaml scipy
/opt/skyforge/training-venv/bin/python -m pip freeze > /mnt/d/dronathon/artifacts/training-requirements.lock.txt
