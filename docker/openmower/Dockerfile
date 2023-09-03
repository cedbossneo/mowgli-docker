## Quickfix while waiting for OpenMower to fix multi-arch build
# Get an image with git and apt-get update
FROM ghcr.io/clemenselflein/open_mower_ros:main

# Set timezone
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Patch OpenMower
ADD patch.sh /tmp/patch.sh
RUN /tmp/patch.sh


# Install rosserial
RUN mkdir -p /home/ubuntu/rosserial/src && cd /home/ubuntu/rosserial/src && git clone https://github.com/tongtybj/rosserial && cd rosserial && git checkout rosservice_server
USER root
RUN bash -c 'source /opt/ros/noetic/setup.bash && cd /home/ubuntu/rosserial && catkin_make -DCMAKE_INSTALL_PREFIX=/opt/ros/noetic install --only-pkg-with-deps rosserial_server'

ADD scripts /home/ubuntu/scripts

CMD [ "/home/ubuntu/scripts/start_mowgli.sh" ]
