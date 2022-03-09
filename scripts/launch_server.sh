#!/bin/bash

set -o nounset
set -o errexit

KEMTLS_FOLDER=kemtls-server-reproducible
CERT_DIR_LOCAL=${KEMTLS_FOLDER}/certs/

if [ ! -d $KEMTLS_FOLDER ]; then
    echo "No '$KEMTLS_FOLDER' folder. Are you in the experiments root dir?"
    exit 1
fi

if [ $# -lt 3 ] ; then
    echo "SIGN_ALGORITHM, KEM_ALGORITHM or testcase number not set. Call: $0 SIGN_ALGO KEM_ALGO TESTCASE_NUM"
    echo "Example: $0 falcon512 lightsaber 1"
    exit 1
fi

SIGN_ALGORITHM=$1
KEM_ALGORITHM=$2
TESTCASE_NUM=$(printf "%04d" $3)

TESTCASE_PATH=${SIGN_ALGORITHM}_${KEM_ALGORITHM}_${TESTCASE_NUM}
TESTCASE_LOCAL_PATH=${CERT_DIR_LOCAL}/${TESTCASE_PATH}
TESTCASE_CERT=${TESTCASE_LOCAL_PATH}.crt
TESTCASE_KEY=${TESTCASE_LOCAL_PATH}.key

SERVER_BIN=${KEMTLS_FOLDER}/kemtls-experiment/rustls/target/debug/examples/tlsserver

if [ -e ${TESTCASE_CERT} -a -e ${TESTCASE_KEY} ]; then
    echo "Test case found!"
else
    echo "Test case files '${TESTCASE_CERT}' not found."
    exit 1
fi

if [ -e ${SERVER_BIN} ]; then
    echo "Using already build server. **NOT** rebuilding."
else
    echo "No prebuild server available."
    cd $KEMTLS_FOLDER
    echo "Building Rust server in Docker."
    docker-compose run builder bash /mnt/scripts/build_server.sh
    cd ..
fi

echo "Launching server."
${SERVER_BIN} -p 4443 --certs $TESTCASE_CERT --key $TESTCASE_KEY --verbose echo
