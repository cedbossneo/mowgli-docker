# Stage 1: grab pre-built mower_msgs / xbot_msgs Python packages from OpenMower
ARG OM_IMAGE=ghcr.io/cedbossneo/mowgli-docker:upstream
FROM ${OM_IMAGE} AS om-msgs

# Stage 2: main image
FROM ros:noetic-ros-base

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    python3-pip \
    libeigen3-dev \
    ros-noetic-tf \
    ros-noetic-tf2-ros \
    ros-noetic-nav-msgs \
    ros-noetic-sensor-msgs \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy OpenMower Python packages (messages, services, map)
COPY --from=om-msgs /opt/open_mower_ros/devel/lib/python3/dist-packages/mower_msgs \
    /opt/ros/noetic/lib/python3/dist-packages/mower_msgs
COPY --from=om-msgs /opt/open_mower_ros/devel/lib/python3/dist-packages/mower_map \
    /opt/ros/noetic/lib/python3/dist-packages/mower_map
COPY --from=om-msgs /opt/open_mower_ros/devel/lib/python3/dist-packages/xbot_msgs \
    /opt/ros/noetic/lib/python3/dist-packages/xbot_msgs
COPY --from=om-msgs /opt/open_mower_ros/devel/lib/python3/dist-packages/xbot_positioning \
    /opt/ros/noetic/lib/python3/dist-packages/xbot_positioning

# Build rf2o_laser_odometry (ROS1 fork - for laser odom)
RUN mkdir -p /catkin_ws/src && \
    cd /catkin_ws/src && \
    git clone https://github.com/phuwanat-vg/rf2o_laser_odometry_ros1.git rf2o_laser_odometry && \
    cd /catkin_ws && \
    bash -c 'source /opt/ros/noetic/setup.bash && catkin_make'

ADD scripts /scripts
RUN chmod +x /scripts/*.sh /scripts/*.py

CMD ["/scripts/start_test.sh"]
