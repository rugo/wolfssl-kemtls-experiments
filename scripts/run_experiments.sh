#!/bin/bash

set -o nounset
set -o errexit

trap "pkill -f tlsserver" EXIT

SIG_ALGS="falcon512 dilithium2 rainbowIclassic"
KEM_ALGS="kyber512 lightsaber ntruhps2048509"
SERVER_PORT=4443
ZEPHYR_WORKSPACE=kemtls-experiment
ZEPHYR_ELF_PATH=zephyr-docker/zephyr_workspaces/${ZEPHYR_WORKSPACE}/build/zephyr/zephyr.elf

if [ "$#" -gt 0 ]; then
    DIR_NAME=$1
else
    DIR_NAME=$(date --iso-8601=seconds)
fi
BENCHMARKS_DIR="benchmarks/kemtls/${DIR_NAME}"

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



for CERT_SIG_ALG in $SIG_ALGS; do
    for CERT_KEM_ALG in $KEM_ALGS; do
        for KEX_ALG in $KEM_ALGS; do
            echo "Conducting experiments for CERT=[${CERT_SIG_ALG},${CERT_KEM_ALG}], KEX=${KEX_ALG}."
            for i in {1..2}; do
                BENCHMARK_PATH=${BENCHMARKS_DIR}/${KEX_ALG}_${CERT_SIG_ALG}_${CERT_KEM_ALG}_${i}.txt
                echo " Starting round ${i}..."
                echo "  Launching server"
                scripts/launch_server.sh ${CERT_SIG_ALG} ${CERT_KEM_ALG} $i > /dev/null 2>&1 &
                echo "  Waiting for server to come up"
                SERVER_UP="n"
                for j in {1..10}; do
                    NC_RET=$(lsof -i4 -iTCP:${SERVER_PORT}|echo "$?")
                    if [ "$NC_RET" -eq "0" ]; then
                        SERVER_UP="y"
                        break;
                    fi
                    echo "  Server didn't come up yet."
                    sleep 2
                done

                if [ "$SERVER_UP" == "n" ]; then
                    echo "  Server didn't start. Exiting."
                    exit 1
                fi
                echo "  Preparing build of zephyr/wolfssl"
                scripts/build_header.py $KEX_ALG $CERT_SIG_ALG $CERT_KEM_ALG $i
                echo "  Building zephyr/wolfssl"
                scripts/build_wolfssl.sh
                # run ROM analysis only on first build, because its slow
                # and doesnt change for different keys.
                if [ $i -eq 1 ]; then
                    echo " Running ROM analysis"
                    scripts/rom_report_wolfssl.sh $ZEPHYR_WORKSPACE|scripts/filter_rom_report.py > ${BENCHMARK_PATH}
                    echo " Reading overall .text segment size"
                    ELF_SIZE=$(arm-none-eabi-size $ZEPHYR_ELF_PATH | tail -n 1 | cut -d' ' -f2)
                    echo "elf_text_size,${ELF_SIZE}" >> ${BENCHMARK_PATH}
                fi
                echo "  Flashing zephyr to board"
                scripts/flash_zephyr.sh
                echo "  Waiting for handshake to finish"
                ./scripts/recv_benchmarks.py >> ${BENCHMARK_PATH}
                echo "  Killing server"
                pkill -f tlsserver
            done
        done
    done
done
