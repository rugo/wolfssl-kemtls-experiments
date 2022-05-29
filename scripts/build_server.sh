#!/bin/bash

set -o nounset
set -o errexit

KEMTLS_FOLDER=kemtls-server-reproducible
cd $KEMTLS_FOLDER
echo "Building Rust server in Docker."
docker-compose run builder bash /mnt/scripts/build_server.sh
cd ..

