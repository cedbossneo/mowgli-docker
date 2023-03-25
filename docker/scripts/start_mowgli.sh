#!/bin/bash
echo "Starting ROS Core..."
/opt/ros/noetic/bin/roscore &
sleep 5
echo "Starting ROS Serial..."
/opt/ros/noetic/bin/rosrun rosserial_python serial_node.py _port:=/dev/mowgli _baud:=115200 &
sleep 5
echo "Starting Mowgli"
source ~/MowgliRover/src/mowgli/config/mowgli_config.sh
roslaunch mowgli mowgli.launch
