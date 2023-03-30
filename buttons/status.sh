#!/bin/bash
docker-compose exec mowgli /entrypoint.sh rostopic echo /mower/status
