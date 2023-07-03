#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec openmower /entrypoint.sh /home/ubuntu/open_mower_ros/utils/mower_buttons/press_home.sh
