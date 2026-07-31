## Quickfix while waiting for OpenMower to fix multi-arch build
# Get an image with git and apt-get update
FROM ghcr.io/jeremysalwen/open_mower_ros:main

USER root
# Set timezone
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Patch OpenMower
ADD patch.sh /tmp/patch.sh
RUN /tmp/patch.sh
RUN bash -c 'source /openmower_entrypoint.sh && catkin_make'

ADD scripts /home/ubuntu/scripts

CMD [ "/home/ubuntu/scripts/start_mowgli.sh" ]
