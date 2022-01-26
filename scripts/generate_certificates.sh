#!/bin/bash

set -o nounset
set -o errexit

KEMTLS_FOLDER=kemtls-server-reproducible
if [ ! -d $KEMTLS_FOLDER ]; then
    echo "No '$KEMTLS_FOLDER' folder. Are you in the experiments root dir?"
    exit 1
fi

cd $KEMTLS_FOLDER
echo "Running certificate builder in Docker."
docker-compose run builder bash /mnt/scripts/gen_key.sh
