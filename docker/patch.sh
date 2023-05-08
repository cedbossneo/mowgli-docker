#!/bin/bash
set -xe
echo "Patching OM"
sed -i 's/output="screen"/unless="\$\(optenv OM_NO_COMMS True\)" output="screen"/g' /home/ubuntu/open_mower_ros/src/open_mower/launch/include/_comms.launch
