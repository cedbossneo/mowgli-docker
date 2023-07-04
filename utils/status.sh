#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec -it openmower /openmower_entrypoint.sh rostopic echo --clear /mower/status
