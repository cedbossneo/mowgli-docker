#!/bin/bash
docker run --net=host -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY -h $HOSTNAME -v $HOME/.Xauthority:/home/ubuntu/.Xauthority cedbossneo/mowgli roslaunch open_mower remote_rviz.launch
