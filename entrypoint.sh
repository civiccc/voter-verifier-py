#!/bin/bash
set -euo pipefail

mkdir -p ${APP_DIRECTORY:-/app}
chown $UID:$GID ${APP_DIRECTORY:-/app}

# TODO: do this conditionally if they are defined, and make sure you can't set
# UID=1.
groupadd -f app
groupmod --non-unique -g $GID app
usermod --non-unique -u $UID -g $GID app

docker_host=$(ip route | grep default | awk '{ print $3 }')
echo "${docker_host} docker-host" >> /etc/hosts

cd ${APP_DIRECTORY:-/app}
gosu app "$@"
