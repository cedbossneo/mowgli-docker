#!/bin/bash
echo "Starting OpenMower GPS"
source /home/ubuntu/open_mower_ros/src/open_mower/config/mower_config.sh
roslaunch /home/ubuntu/open_mower_ros/src/open_mower/launch/include/_gps.launch
