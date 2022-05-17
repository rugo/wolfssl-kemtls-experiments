#!/bin/bash

set -o nounset
set -o errexit

CERT_DIR_LOCAL=OQS/certs/
CERT_DIR_ABSOLUTE=$(pwd)/${CERT_DIR_LOCAL}

if [ ! -d $CERT_DIR_LOCAL ]; then
    echo "No '$CERT_DIR_LOCAL' folder. Are you in the experiments root dir?"
    exit 1
fi

if [ $# -lt 4 ] ; then
    echo "SIGN_ROOT_ALGORITHM, SIGN_LEAF_ALGORITHM, KEM_ALGORITHM or testcase number not set. Call: $0 SIGN_ROOT_ALGO SIGN_LEAF_ALGO KEM_ALGO TESTCASE_NUM"
    echo "Example: $0 falcon512 lightsaber 1"
    exit 1
fi

SIGN_ROOT_ALGORITHM=$1
SIGN_LEAF_ALGORITHM=$2
KEM_ALGORITHM=$3
TESTCASE_NUM=$(printf "%04d" $4)

TESTCASE_PATH=${SIGN_ROOT_ALGORITHM}_${SIGN_LEAF_ALGORITHM}_${TESTCASE_NUM}
TESTCASE_LOCAL_PATH=${CERT_DIR_ABSOLUTE}/${TESTCASE_PATH}
TESTCASE_CERT=${TESTCASE_LOCAL_PATH}.crt
TESTCASE_KEY=${TESTCASE_LOCAL_PATH}.key

SERVER_WOLFSSL_PATH=zephyr-docker/zephyr_workspaces/pqtls-experiment/modules/crypto/wolfssl
SERVER_BUILD_DIR=${SERVER_WOLFSSL_PATH}/build_server
SERVER_BIN=pqtls_server
SERVER_BIN_PATH=${SERVER_BUILD_DIR}/${SERVER_BIN}

if [ ! -d $SERVER_WOLFSSL_PATH ]; then
    echo "No '$SERVER_WOLFSSL_PATH' folder. Are you in the experiments root dir?"
    exit 1
fi

if [ ! -d $SERVER_BUILD_DIR ]; then
    echo "Build dir '$SERVER_BUILD_DIR' does not exist yet. Creating."
    mkdir $SERVER_BUILD_DIR
fi

if [ -e ${TESTCASE_CERT} -a -e ${TESTCASE_KEY} ]; then
    echo "Test case found!"
else
    echo "Test case files '${TESTCASE_CERT}' not found."
    exit 1
fi

if [ -e ${SERVER_BIN_PATH} ]; then
    echo "pqtls server binary already exists. rebuilding."
fi

EXP_DIR=$(pwd)

cd $SERVER_BUILD_DIR
cmake ..
make pqtls_server
