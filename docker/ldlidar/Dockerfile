FROM ros:noetic-ros-base

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    libeigen3-dev \
    python3-numpy \
    ros-noetic-tf \
    ros-noetic-tf2-ros \
    ros-noetic-nav-msgs \
    ros-noetic-sensor-msgs \
    && rm -rf /var/lib/apt/lists/*

# Build ldlidar_stl_ros driver and rf2o_laser_odometry (both catkin)
RUN mkdir -p /catkin_ws/src && \
    cd /catkin_ws/src && \
    git clone https://github.com/ldrobotSensorTeam/ldlidar_stl_ros.git && \
    git clone https://github.com/phuwanat-vg/rf2o_laser_odometry_ros1.git rf2o_laser_odometry && \
    cd /catkin_ws && \
    bash -c 'source /opt/ros/noetic/setup.bash && catkin_make'

ADD scripts /scripts
RUN chmod +x /scripts/*.sh

CMD ["/scripts/start_lidar.sh"]
