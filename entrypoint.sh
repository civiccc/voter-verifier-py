#!/bin/bash
set -exuo pipefail

if [ ${APP_DIRECTORY} != "/app" ]; then
  rm -rf /app
  ln -sfT $APP_DIRECTORY /app
fi

chown $UID:$GID /app

# TODO: do this conditionally if they are defined, and make sure you can't set
# UID=1.
groupadd -f app
groupmod --non-unique -g $GID app
usermod --non-unique -u $UID -g $GID app

docker_host=$(ip route | grep default | awk '{ print $3 }')
echo "${docker_host} docker-host" >> /etc/hosts

cd /app
gosu app "$@"
