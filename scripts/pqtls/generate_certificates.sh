#!/bin/bash

set -o nounset
set -o errexit

OQS_FOLDER=OQS
CERT_FOLDER=${OQS_FOLDER}/certs

if [ ! -d $OQS_FOLDER ]; then
    echo "No '$OQS_FOLDER' folder. Are you in the experiments root dir?"
    exit 1
fi

if [ ! -d $CERT_FOLDER ]; then
    echo "No '$CERT_FOLDER' folder. Creating."
    mkdir -p $CERT_FOLDER
fi

cd $OQS_FOLDER
echo "Running certificate builder in Docker."
docker-compose run builder sh /mnt/scripts/gen_certs.sh