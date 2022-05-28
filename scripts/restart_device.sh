#!/bin/bash
set -o nounset
set -o errexit

echo "r                                                                                                                                            [0]
g
qc"|JLinkExe -device EFM32GG11B820F2048GL192 -speed 4000 -if SWD