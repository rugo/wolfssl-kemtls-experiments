#!/bin/bash

set -o nounset
set -o errexit

source ~/fun/venv310/bin/activate

sudo tc qdisc add dev enp0s20f0u1 root netem delay 13ms rate 1mbit

./scripts/pqtls/run_experiments.sh 1mbit_13msdelay >  1.log 2>&1
./scripts/run_experiments.sh 1mbit_13msdelay_elf_size

sudo tc qdisc del dev enp0s20f0u1 root netem delay 13ms rate 1mbit

sudo tc qdisc add dev enp0s20f0u1 root netem delay 60ms rate 1mbit

./scripts/pqtls/run_experiments.sh 1mbit_60msdelay > pq160.log 2>&1 || true
./scripts/run_experiments.sh 1mbit_60msdelay_elf_size

sudo tc qdisc del dev enp0s20f0u1 root netem delay 60ms rate 1mbit


sudo tc qdisc add dev enp0s20f0u1 root netem delay 1500ms rate 46kbit

./scripts/pqtls/run_experiments.sh 46kbit_1500msdelay > pq461500.log 2>&1 || true
./scripts/run_experiments.sh 46kbit_1500msdelay_elf_size

sudo tc qdisc del dev enp0s20f0u1 root netem delay 1500ms rate 46kbit
