#!/bin/sh

set -o nounset
set -o errexit

SIG_ALGS="falcon512 dilithium2 rainbowIclassic"
TARGET_DIR="/mnt/certs"
SSL_DIR=/opt/oqssa
SSL_BIN=${SSL_DIR}/bin/openssl

if [ ! -d  $TARGET_DIR ]; then
    mkdir -p $TARGET_DIR
fi

for ROOT_SIG_ALG in $SIG_ALGS; do
    for LEAF_SIG_ALG in $SIG_ALGS; do
        for i in $(seq 1 1000); do
            NUM=$(printf "%04d" $i)
            echo "Doing ${ROOT_SIG_ALG}x${LEAF_SIG_ALG} number ${NUM} now."
            BASENAME=${TARGET_DIR}/${ROOT_SIG_ALG}_${LEAF_SIG_ALG}_${NUM}
            ${SSL_BIN} req -x509 -new -newkey ${ROOT_SIG_ALG} -keyout ${BASENAME}_ca.key -out ${BASENAME}_ca.crt -nodes -subj "/CN=ThomCert CA" -days 365 -config ${SSL_DIR}/ssl/openssl.cnf
            ${SSL_BIN} req -new -newkey ${LEAF_SIG_ALG} -keyout ${BASENAME}.key -out ${BASENAME}.csr -nodes -subj "/CN=servername" -config ${SSL_DIR}/ssl/openssl.cnf
            ${SSL_BIN} x509 -req -in ${BASENAME}.csr -out ${BASENAME}.crt -CA ${BASENAME}_ca.crt -CAkey ${BASENAME}_ca.key -CAcreateserial -days 365
            rm ${BASENAME}.csr
        done
    done
done
