#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
$SCRIPT_DIR/call.sh exec openmower /openmower_entrypoint.sh rosservice call /mowgli/Reboot
