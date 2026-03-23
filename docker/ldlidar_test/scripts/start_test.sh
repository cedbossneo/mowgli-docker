#!/bin/bash
echo "Starting mower simulation for offline testing"

source /opt/ros/noetic/setup.bash

# Source catkin workspace (rf2o)
if [ -f /catkin_ws/devel/setup.bash ]; then
  source /catkin_ws/devel/setup.bash
fi

# Wait for roscore to be fully ready
echo "Waiting for roscore..."
until rostopic list > /dev/null 2>&1; do
  sleep 1
done
echo "roscore is ready"

# Full simulation mode (default) or lidar-only mode
SIM_MODE=${SIM_MODE:-full}

if [ "$SIM_MODE" = "full" ]; then
  echo "=== Full Mower Simulation ==="
  echo "  Pattern: ${SIM_PATTERN:-rectangle}"
  echo "  Speed: ${SIM_SPEED:-0.3} m/s"
  echo "  GPS fix ratio: ${SIM_GPS_FIX_RATIO:-0.7}"
  echo "  Obstacles: ${SIM_OBSTACLES:-3:4:0.3,7:2:0.5,5:6:0.4}"

  # Start full simulation (GPS + odom + IMU + lidar + TF)
  python3 /scripts/fake_mower_sim.py &
  SIM_PID=$!

  # Start laser odometry in background if enabled
  if [ "${LIDAR_ODOM_ENABLE:-false}" = "true" ]; then
    sleep 3
    echo "Laser odometry enabled - starting rf2o"
    roslaunch /scripts/laser_odometry.launch \
      laser_scan_topic:=${LIDAR_TOPIC:-/scan} \
      base_frame_id:=base_link \
      odom_frame_id:=odom_laser &
  fi

  # Start ICP localization for GPS FLOAT recovery
  if [ "${ICP_ENABLE:-false}" = "true" ]; then
    sleep 5
    echo "ICP localization enabled - starting icp_localization"
    python3 /scripts/icp_localization.py &
  fi

  wait $SIM_PID
else
  echo "=== Lidar-Only Mode ==="
  # Start fake lidar first
  python3 /scripts/fake_lidar.py &
  LIDAR_PID=$!
  sleep 2

  if [ "${LIDAR_ODOM_ENABLE:-false}" = "true" ]; then
    echo "Laser odometry enabled - starting rf2o"
    roslaunch /scripts/laser_odometry.launch \
      laser_scan_topic:=${LIDAR_TOPIC:-/scan} \
      base_frame_id:=base_link \
      odom_frame_id:=odom_laser &
  fi

  wait $LIDAR_PID
fi
