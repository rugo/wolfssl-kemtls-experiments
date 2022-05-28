#!/bin/bash

set -o nounset
set -o errexit

trap "pkill -f pqtls_server" EXIT

SIG_ALGS="dilithium2 falcon512"
KEM_ALGS="kyber512 lightsaber ntruhps2048509"
SERVER_PORT=4443
ZEPHYR_WORKSPACE=pqtls-experiment
ZEPHYR_ELF_PATH=zephyr-docker/zephyr_workspaces/${ZEPHYR_WORKSPACE}/build/zephyr/zephyr.elf

IFACE_NAME=enp0s20f0u1
NUM_ITERS=1000

TC_PARAMS=("dev ${IFACE_NAME} root netem delay 13ms rate 1mbit" "dev ${IFACE_NAME} root netem delay 60ms rate 1mbit" "dev ${IFACE_NAME} root netem delay 1500ms rate 46kbit")
TC_PARAMS_NAMES=("1mbit_13msdelay" "1mbit_60msdelay" "46kbit_1500msdelay")


BENCHMARKS_DIR="benchmarks/pqtls/"

HOST_IP="192.0.2.1"
IP_SET=$(ip a|grep ${HOST_IP}|echo $?)

if [ "$IP_SET" -ne "0" ]; then
    echo "No ethernet interface is set to the IP ${HOST_IP}! Exiting."
    exit 1
fi

python -c "import serial" > /dev/null 2>&1 || (echo "pyserial not installed" && exit 1)

for TC_NUM in $(seq 0 2); do
    BENCHMARK_SUBDIR=${BENCHMARKS_DIR}/${TC_PARAMS_NAMES[$TC_NUM]}
    if [ ! -d $BENCHMARK_SUBDIR ]; then
        echo "Benchmark dir '${BENCHMARK_SUBDIR}' does not exist. Creating it now."
        mkdir -p $BENCHMARK_SUBDIR
    else
        echo "Benchmark dir '${BENCHMARK_SUBDIR}' exists. Please clear first."
        # exit 1
    fi
done


for ROOT_SIG_ALG in $SIG_ALGS; do
  for LEAF_SIG_ALG in $SIG_ALGS; do
    for KEX_ALG in $KEM_ALGS; do
        echo "Conducting experiments for CERT=[${ROOT_SIG_ALG},${LEAF_SIG_ALG}], KEX=${KEX_ALG}."|tee -a progress.log
        for i in {1..${NUM_ITERS}}; do
            echo "At iteration ${i}"|tee -a progress.log
            BENCHMARK_PATH=${BENCHMARKS_DIR}/${TC_PARAMS_NAMES[0]}/${ROOT_SIG_ALG}_${LEAF_SIG_ALG}_${KEX_ALG}_${i}.txt
            if [ -e $BENCHMARK_PATH ]; then
                echo $BENCHMARK_PATH already exists. Skipping.
                continue
            fi

            echo "  Patching headers of zephyr/wolfssl"
            scripts/pqtls/build_header.py $KEX_ALG $ROOT_SIG_ALG $LEAF_SIG_ALG $i

            echo "  Building zephyr/wolfssl"
            scripts/pqtls/build_wolfssl.sh
            # run ROM analysis only on first build, because its slow
            # and doesnt change for different keys.
            if [ $i -eq 1 ]; then
                echo "  Running ROM analysis"
                scripts/rom_report_wolfssl.sh $ZEPHYR_WORKSPACE|scripts/filter_rom_report.py > ${BENCHMARK_PATH}
                echo " Reading overall .text segment size"
                ELF_SIZE=$(arm-none-eabi-size $ZEPHYR_ELF_PATH | tail -n 1 | cut -d' ' -f2)
                echo "elf_text_size,${ELF_SIZE}" >> ${BENCHMARK_PATH}
            fi
            echo "  Flashing zephyr to board"
            scripts/pqtls/flash_zephyr.sh

            echo "  Building server for algorithm combination  CERT=[${ROOT_SIG_ALG},${LEAF_SIG_ALG}], KEX=${KEX_ALG}."
            scripts/pqtls/build_server.sh $ROOT_SIG_ALG ${LEAF_SIG_ALG} $KEX_ALG $i

            for TC_NUM in $(seq 0 2); do
                    BENCHMARK_PATH=${BENCHMARKS_DIR}/${TC_PARAMS_NAMES[$TC_NUM]}/${ROOT_SIG_ALG}_${LEAF_SIG_ALG}_${KEX_ALG}_${i}.txt
                    echo " Resetting qdisc"
                    sudo tc qdisc del dev enp0s20f0u1 root||true
                    echo " Adding network parameters: $(echo ${TC_PARAMS[$TC_NUM]})"|tee -a progress.log
                    sudo tc qdisc add $(echo ${TC_PARAMS[$TC_NUM]})
                    echo " Starting round ${i} with ${TC_PARAMS_NAMES[$TC_NUM]}..."
                    echo "  Launching server"
                    scripts/pqtls/launch_server.sh $ROOT_SIG_ALG ${LEAF_SIG_ALG} $KEX_ALG $i > /tmp/pqtls_server.log 2>&1 &

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

                    echo "  Server Up. Reseting Board."
                    ./scripts/restart_device.sh
                    echo "  Waiting for handshake to finish"
                    ./scripts/recv_benchmarks.py >> ${BENCHMARK_PATH}
                    echo "  Killing server"
                    pkill -f pqtls_server
            done
        done
    done
  done
done
