#!/bin/bash
docker run --net=host -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY -h $HOSTNAME -v $HOME/.Xauthority:/root/.Xauthority ghcr.io/cedbossneo/mowgli-docker:cedbossneo-arm64 roslaunch open_mower remote_rviz.launch
