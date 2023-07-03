#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec -it openmower /entrypoint.sh rostopic echo --clear -w 5 /xbot_driver_gps/xb_pose
