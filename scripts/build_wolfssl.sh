#!/bin/bash

set -o nounset
set -o errexit

ZEPHYR_DIR=zephyr-docker
BUILD_SCRIPT=/root/scripts/build.sh

if [ ! -d $ZEPHYR_DIR ]; then
    echo "No '$ZEPHYR_DIR' folder. Are you in the experiments root dir?"
    exit 1
fi

cd $ZEPHYR_DIR

echo "Starting build."
docker-compose run builder bash $BUILD_SCRIPT $@
