#!/bin/bash
echo "Starting OpenMower"
source /config/mower_config.sh
roslaunch open_mower open_mower.launch
