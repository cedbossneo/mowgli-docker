#!/bin/bash
echo "Starting LDRobot LD19 lidar driver"

source /catkin_ws/devel/setup.bash

# Start laser odometry in background if enabled (for GPS recovery)
if [ "${LIDAR_ODOM_ENABLE:-false}" = "true" ]; then
  echo "Laser odometry enabled - starting rf2o in background"
  roslaunch /scripts/laser_odometry.launch \
    laser_scan_topic:=${LIDAR_TOPIC:-/scan} \
    base_frame_id:=base_link \
    odom_frame_id:=odom_laser &
fi

# Start ICP scan matching for GPS FLOAT recovery if enabled
if [ "${ICP_ENABLE:-false}" = "true" ]; then
  echo "ICP localization enabled - starting icp_localization in background"
  sleep 5
  python3 /scripts/icp_localization.py &
fi

roslaunch --wait ldlidar_stl_ros ld19.launch \
  port_name:=${LIDAR_PORT:-/dev/ttyUSB0} \
  topic_name:=${LIDAR_TOPIC:-/scan} \
  frame_id:=${LIDAR_FRAME_ID:-base_laser} \
  fix_to_base_link:=${LIDAR_FIX_TF:-true}
