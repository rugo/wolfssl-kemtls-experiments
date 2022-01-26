#!/bin/bash

set -o nounset
set -o errexit

KEMTLS_FOLDER=kemtls-server-reproducible
PATCHED_ENCODER=scripts/updates/encoder.py
MKCERT_PATH=kemtls-reproducible/kemtls-experiment/mk-cert

if [ ! -d $KEMTLS_FOLDER ]; then
    echo "No '$KEMTLS_FOLDER' folder. Are you in the experiments root dir?"
    exit 1
fi

if [ ! -d $MKCERT_PATH ]; then
    echo "No '$MKCERT_PATH' folder. Are you in the experiments root dir and did you clone with --recurse-submodules?"
    exit 2
fi

echo "Patching certificate encoder."
cp $PATCHED_ENCODER $MKCERT_PATH

cd $KEMTLS_FOLDER
echo "Running certificate builder in Docker."
docker-compose run builder bash /mnt/scripts/gen_key.sh
