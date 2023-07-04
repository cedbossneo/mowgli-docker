#!/bin/bash
echo "Starting OpenMower"
source /opt/open_mower_ros/src/open_mower/config/mower_config.sh
roslaunch open_mower open_mower.launch
