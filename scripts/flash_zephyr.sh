#!/bin/bash

set -o nounset
set -o errexit

DEFAULT_PATH="zephyr-docker/zephyr_workspaces/kemtls-experiment/build/zephyr/zephyr.bin"

if [ ! -e $DEFAULT_PATH ]; then
    echo "The binary ${DEFAULT_PATH} does not exist!"
    exit 1
fi

scripts/flash.sh $DEFAULT_PATH
