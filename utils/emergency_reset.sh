#!/bin/bash
docker compose exec openmower /entrypoint.sh rosservice call /mower_service/emergency 0
