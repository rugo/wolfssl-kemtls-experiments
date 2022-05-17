#!/bin/bash

set -o nounset
set -o errexit

trap "pkill -f pqtls_server" EXIT

SIG_ALGS="dilithium2 falcon512"
KEM_ALGS="kyber512 lightsaber ntruhps2048509"
SERVER_PORT=4443
BENCHMARKS_DIR="benchmarks/pqtls/$(date --iso-8601=seconds)"
ZEPHYR_WORKSPACE=pqtls-experiment

HOST_IP="192.0.2.1"
IP_SET=$(ip a|grep ${HOST_IP}|echo $?)

if [ "$IP_SET" -ne "0" ]; then
    echo "No ethernet interface is set to the IP ${HOST_IP}! Exiting."
    exit 1
fi

python -c "import serial" > /dev/null 2>&1 || (echo "pyserial not installed" && exit 1)

if [ ! -d $BENCHMARKS_DIR ]; then
    echo "Benchmark dir '${BENCHMARKS_DIR}' does not exist. Creating it now."
    mkdir -p $BENCHMARKS_DIR
fi



for ROOT_SIG_ALG in $SIG_ALGS; do
  for LEAF_SIG_ALG in $SIG_ALGS; do
    for KEX_ALG in $KEM_ALGS; do
        echo "Conducting experiments for CERT=[${ROOT_SIG_ALG},${LEAF_SIG_ALG}], KEX=${KEX_ALG}."
        for i in {1..2}; do
            BENCHMARK_PATH=${BENCHMARKS_DIR}/${ROOT_SIG_ALG}_${LEAF_SIG_ALG}_${KEX_ALG}_${i}.txt
            echo " Starting round ${i}..."
            echo "  Patching headers of zephyr/wolfssl"
            scripts/pqtls/build_header.py $KEX_ALG $ROOT_SIG_ALG $LEAF_SIG_ALG $i

            if [ $i -eq 1 ]; then
                echo "  Building server for algorithm combination  CERT=[${ROOT_SIG_ALG},${LEAF_SIG_ALG}], KEX=${KEX_ALG}."
                 scripts/pqtls/build_server.sh $ROOT_SIG_ALG ${LEAF_SIG_ALG} $KEX_ALG $i
            fi

            echo "  Launching server"
            scripts/pqtls/launch_server.sh $ROOT_SIG_ALG ${LEAF_SIG_ALG} $KEX_ALG $i > /dev/null 2>&1 &

            echo "  Waiting for server to come up"
            SERVER_UP="n"
            for j in {1..10}; do
                NC_RET=$(lsof -i4 -iTCP:${SERVER_PORT}|echo "$?")
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
            echo "  Building zephyr/wolfssl"
            scripts/pqtls/build_wolfssl.sh
            # run ROM analysis only on first build, because its slow
            # and doesnt change for different keys.
            if [ $i -eq 1 ]; then
                echo "  Running ROM analysis"
                scripts/rom_report_wolfssl.sh $ZEPHYR_WORKSPACE|scripts/filter_rom_report.py > ${BENCHMARK_PATH}
            fi
            echo "  Flashing zephyr to board"
            scripts/pqtls/flash_zephyr.sh
            echo "  Waiting for handshake to finish"
            ./scripts/recv_benchmarks.py >> ${BENCHMARK_PATH}
            echo "  Killing server"
            pkill -f pqtls_server
        done
    done
  done
done
