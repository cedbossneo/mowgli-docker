FROM ubuntu:20.04

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y curl git gnupg iproute2 sudo
RUN echo "deb http://packages.ros.org/ros/ubuntu focal main" > /etc/apt/sources.list.d/ros-latest.list
RUN curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | apt-key add -

RUN apt update && apt install -y ros-noetic-ros-base

RUN adduser ubuntu
RUN adduser ubuntu sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN apt-get -y install g++ cpp cmake ros-noetic-tf2-eigen ros-noetic-teleop-twist-keyboard ros-noetic-robot-state-publisher ros-noetic-joint-state-publisher ros-noetic-map-server ros-noetic-rosserial-server ros-noetic-gps-common picocom   ros-noetic-tf2-geometry-msgs ros-noetic-robot-localization libpigpiod-if-dev wavemon ros-noetic-rosserial-arduino python3-paho-mqtt openocd python3-rosdep ros-noetic-rtcm-msgs libxml2-utils python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool build-essential
RUN echo export ROS_IP=localhost > /opt/ros/noetic/setup.bash
RUN echo export ROS_MASTER_URI=http://localhost:11311 >> /opt/ros/noetic/setup.bash
RUN echo CATKIN_SHELL=bash >> /opt/ros/noetic/setup.bash
RUN echo 'source /opt/ros/noetic/setup.sh' >> /opt/ros/noetic/setup.bash

USER ubuntu

RUN echo "source /opt/ros/noetic/setup.bash" >> /home/ubuntu/.bashrc
RUN echo "source /home/ubuntu/MowgliRover/devel/setup.bash" >> /home/ubuntu/.bashrc
RUN echo 'alias depit="rosdep install --from-paths src --ignore-src -r -y"' >> /home/ubuntu/.bashrc
RUN echo 'alias debug="picocom -b 115200 /dev/ttyAMA1"' >> /home/ubuntu/.bashrc
RUN echo 'alias vbat="rostopic echo -n 1 /mowgli/status/v_battery | head -1"' >> /home/ubuntu/.bashrc

ENV HOME=/home/ubuntu 

RUN cd /home/ubuntu && git clone https://github.com/cloudn1ne/MowgliRover.git

RUN bash -c 'cd /home/ubuntu/MowgliRover/ && git submodule update --init --recursive'
RUN cd /home/ubuntu/MowgliRover/src/Mowgli-open_mower_ros/ && git checkout main
RUN cd /home/ubuntu/MowgliRover/src/Mowgli-open_mower_ros/ && git checkout main
RUN cd /home/ubuntu/MowgliRover/src/Mowgli-open_mower_ros/src/lib/slic3r_coverage_planner && git checkout main

RUN sudo rosdep init

RUN bash -c 'source /opt/ros/noetic/setup.bash && cd /home/ubuntu/MowgliRover/ && rosdep update'
RUN bash -c 'source /opt/ros/noetic/setup.bash && rosdep install --from-paths /home/ubuntu/MowgliRover/src --ignore-src --simulate | sed --expression "1d" --expression "s/sudo -H apt-get install/apt-get install --no-install-recommends --yes/g" | sort > /home/ubuntu/apt-install.sh'

RUN chmod +x /home/ubuntu/apt-install.sh && sudo /home/ubuntu/apt-install.sh

RUN bash -c 'source /opt/ros/noetic/setup.bash && cd /home/ubuntu/MowgliRover && ./scripts/build_all.sh'

ADD bridge.conf /home/ubuntu/MowgliRover/src/mowgli/scripts/bridge.conf
ADD press_home.sh /home/ubuntu/press_home.sh
ADD press_start.sh /home/ubuntu/press_start.sh
ADD entrypoint.sh /entrypoint.sh

CMD [ "/entrypoint.sh" ]