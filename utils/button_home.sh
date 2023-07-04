#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec openmower /openmower_entrypoint.sh /opt/open_mower_ros/utils/mower_buttons/press_home.sh
