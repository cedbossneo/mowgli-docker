#!/bin/bash
docker compose exec openmower /entrypoint.sh rosservice call /mowgli/Reboot
