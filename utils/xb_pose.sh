#!/bin/bash
docker compose exec -it openmower /entrypoint.sh rostopic echo --clear -w 5 /xbot_driver_gps/xb_pose
