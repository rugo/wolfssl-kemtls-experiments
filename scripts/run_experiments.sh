#!/bin/bash

set -o nounset
set -o errexit

trap "pkill -f tlsserver" EXIT

SIG_ALGS="falcon512 dilithium2 rainbowIclassic"
KEM_ALGS="kyber512 ntruhps2048509 lightsaber"
SERVER_PORT=4443


for CERT_SIG_ALG in $SIG_ALGS; do
    for CERT_KEM_ALG in $KEM_ALGS; do
        for KEX_ALG in $KEM_ALGS; do
            echo "Conducting experiments for CERT=[${CERT_SIG_ALG},${CERT_KEM_ALG}], KEX=${KEX_ALG}."
            for i in {1..2}; do
                echo " Starting round ${i}..."
                echo "  Launching server"
                scripts/launch_server.sh ${CERT_SIG_ALG} ${CERT_KEM_ALG} $i > /dev/null 2>&1 &
                echo "  Waiting for server to come up"
                SERVER_UP="n"
                for j in {1..10}; do
                    NC_RET=$(nc localhost $SERVER_PORT|echo "$?")
                    if [ "$NC_RET" -eq "0" ]; then
                        SERVER_UP="y"
                        break;
                    fi
                    echo "  Server didn't come up yet."
                done

                if [ "$SERVER_UP" == "n" ]; then
                    echo "  Server didn't start. Exiting."
                    exit 1
                fi
                echo "  Preparing build of zephyr/wolfssl"
                scripts/build_header.py $KEX_ALG $CERT_SIG_ALG $CERT_KEM_ALG $i
                echo "  Building zephyr/wolfssl"
                scripts/build_wolfssl.sh
                echo "  Flashing zephyr to board"
                scripts/flash_zephyr.sh
                echo "  Waiting for handshake to finish"
                # TODO
                sleep 20
                echo "  Killing server"
                pkill -f tlsserver
            done
        done
    done
done