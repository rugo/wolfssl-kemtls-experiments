#!/bin/bash

set -o nounset
set -o errexit

if [ "$#" -gt "0" ]; then
    DEV=$1
else
    DEV=enp0s20f0u1u4 # enp0s20f0u1u4
fi
echo "Trying to set IP to device $DEV"

sudo ip a add 192.0.2.1/24 dev $DEV
