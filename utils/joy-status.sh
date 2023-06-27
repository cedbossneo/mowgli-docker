#!/bin/bash
docker compose exec -it openmower /entrypoint.sh rostopic echo --clear /joy
