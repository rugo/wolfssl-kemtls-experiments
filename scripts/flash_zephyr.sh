#!/bin/bash

set -o nounset
set -o errexit

if [ $# -lt 1 ] ; then
    echo "Binary path not set. Call: $0 PATH_TO_BINARY"
    echo "Example: $0 workspaces/ws_name/build/zephyr/zephyr.bin"
    exit 1
fi

BINARY=$1
JLINK_SCRIPT=scripts/flash.jlink

if [ ! -e $JLINK_SCRIPT ]; then
    echo "No '$JLINK_SCRIPT' file. Are you in the experiments root dir?"
    exit 1
fi

sed "s:BINARY:${BINARY}:g" < $JLINK_SCRIPT > /tmp/flash.jlink

JLinkExe -device EFM32GG11B820F2048GL192 -speed 4000 -if SWD -CommanderScript /tmp/flash.jlink
