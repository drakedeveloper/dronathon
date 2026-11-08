set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export GZ_PARTITION=skyforge-mission
gz service -s /gui/move_to --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req 'data: "x3"'
gz service -s /gui/follow --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req 'data: "x3"'
