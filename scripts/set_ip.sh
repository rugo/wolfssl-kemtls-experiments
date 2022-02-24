#!/bin/bash

set -o nounset
set -o errexit

DEV=enp0s20f0u1u4 # enp0s20f0u1u4
echo "Trying to set IP to device $DEV"

sudo ip a add 192.0.2.1/24 dev $DEV
