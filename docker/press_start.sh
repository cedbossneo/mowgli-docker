#!/bin/bash
source /opt/ros/noetic/setup.bash
source /home/ubuntu/MowgliRover/devel/setup.bash
cd /home/ubuntu/MowgliRover
export ROS_IP=$(/sbin/ip route|awk '/default/ { print $9 }')
export ROS_MASTER_URI=http://localhost:11311
export CATKIN_SHELL=bash
./src/Mowgli-open_mower_ros/utils/mower_buttons/press_start.sh
