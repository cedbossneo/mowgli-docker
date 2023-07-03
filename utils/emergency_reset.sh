#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec openmower /entrypoint.sh rosservice call /mower_service/emergency 0
