#!/bin/bash
sudo chown -Rf ubuntu:users /home/ubuntu/.ros
source /opt/ros/noetic/setup.bash
source /home/ubuntu/MowgliRover/devel/setup.bash
cd /home/ubuntu/MowgliRover
export ROS_IP=$(/sbin/ip route|awk '/default/ { print $9 }')
export ROS_MASTER_URI=http://localhost:11311
export CATKIN_SHELL=bash
echo "Starting ROS Core..."
/opt/ros/noetic/bin/roscore &
sleep 5
echo "Starting ROS Serial..."
/opt/ros/noetic/bin/rosrun rosserial_python serial_node.py _port:=/dev/mowgli _baud:=115200 &
sleep 5
echo "Starting Mowgli"
source ~/MowgliRover/src/mowgli/config/mowgli_config.sh
roslaunch mowgli mowgli.launch
