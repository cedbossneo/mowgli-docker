#!/bin/bash
echo "Starting laser odometry (rf2o) for GPS recovery assistance"

source /catkin_ws/devel/setup.bash

roslaunch --wait /scripts/laser_odometry.launch \
  laser_scan_topic:=${LIDAR_TOPIC:-/scan} \
  base_frame_id:=base_link \
  odom_frame_id:=odom_laser
