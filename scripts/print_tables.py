#!/usr/bin/env python3
import sys
import os
import re
from collections import defaultdict as ddict
import prettytable


BENCHMARK_FILE_RE = r"([A-z0-9]+)_([A-z0-9]+)_([A-z0-9]+)_([0-9]+).txt"
DESIRED_BENCHMARKS = [
    "rom_size_wolfssl",
    "rom_size_PQClean",
    "rom_size_PQM4",
    "rom_size_ca_cert",
    "cycles_wc_pq_make_keypair",
    "cycles_wc_pq_kem_dec",
    "cycles_wc_pq_verify_hash",
    "cycles_wc_pq_kem_encapsulate",
    "cycles_connect",
    "peak_mem",
    "bytes_send",
    "bytes_received",
    "cycles_send",
    "cycles_recv"
]

PQTLS_BENCHMARK_FILE_RE = r"([A-z0-9]+)_([A-z0-9]+)_([0-9]+).txt"
PQTLS_DESIRED_BENCHMARKS = [
    "rom_size_wolfssl",
    "rom_size_PQClean",
    "rom_size_PQM4",
    "rom_size_ca_cert",
    "cycles_wc_pq_make_keypair",
    "cycles_wc_pq_kem_dec",
    "cycles_wc_pq_verify_hash",
   # "cycles_wc_pq_kem_encapsulate",
    "cycles_connect",
    "peak_mem",
    "bytes_send",
    "bytes_received",
    "cycles_send",
    "cycles_recv"
]


def log(msg):
    print("[LOG]", msg, file=sys.stderr)


def read_benchmark_file(path):
    if not os.path.isfile(path):
        raise ValueError(f"Path {path} does not exist or is not a file.")

    benchmarks = {}

    with open(path) as f:
        for l in f.readlines():
            name, val = l.strip().split(",")
            if val.isnumeric():
                val = int(val)
            benchmarks[name] = val

    return benchmarks


def get_benchmarks(path, pqtls=False):
    if not os.path.exists(path):
        raise ValueError(f"Path {path} does not exist.")

    benchmarks_collected = ddict(lambda: ddict(lambda: list()))

    for fname in os.listdir(path):
        try:
            if pqtls:
                cert_sig_alg, kex_alg, testcase_num = re.findall(PQTLS_BENCHMARK_FILE_RE, fname)[0]
            else:
                kex_alg, cert_sig_alg, cert_kem_alg, testcase_num = re.findall(BENCHMARK_FILE_RE, fname)[0]
        except IndexError:
            log(f"Filename doesn't fullfil regex, ignoring: {fname}")
            continue

        benchmarks = read_benchmark_file(os.path.join(path, fname))

        if benchmarks["CMD_finish_success"] != "y":
            raise ValueError(f"Benchmark in file {fname} did not run successfully! Exiting!")

        for name, val in benchmarks.items():
            if pqtls:
                benchmarks_collected[f"{kex_alg}_{cert_sig_alg}"][name].append(val)
            else:
                benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"][name].append(val)

    return benchmarks_collected


def build_average(benchmarks):
    averaged_benchmarks = ddict(lambda: dict())
    for comb in benchmarks:
        # First iteration has all benchmarks
        for bench_name, vals in benchmarks[comb].items():
            if bench_name.startswith("CMD"):
                continue
            averaged_benchmarks[comb][bench_name] = sum(vals)/len(vals)

    return averaged_benchmarks


def round_bignum(num):
    if num > 10**6:
        return round(num / 10**6, 2), "*10^6"
    if num > 10**3:
        return round(num / 10**3, 2), "*10^3"
    return num, ""

def build_table(averaged_bench, pqtls=False):
    des_b = PQTLS_DESIRED_BENCHMARKS if pqtls else DESIRED_BENCHMARKS
    field_names = ["Algorithm Comb."] + des_b

    rows = []

    for comb in averaged_bench:
        row = [comb]
        for bname in des_b:
            num, unit = round_bignum(averaged_bench[comb][bname])
            row.append(f"{num} {unit}")
        rows.append(row)

    return field_names, rows

def print_table(field_names, rows):
    table = prettytable.PrettyTable()
    table.field_names = field_names
    table.add_rows(rows)

    print(table)




def main():
    if len(sys.argv) < 2:
        log(f"Error, missing argument. Call: {sys.argv[0]} BENCHMARKS_DIR")
        sys.exit(1)

    # Wow, I'm lazy today... Well, my head hurts...
    pqtls = "--pqtls" in sys.argv
    benchmarks = get_benchmarks(sys.argv[1], pqtls)

    avg = build_average(benchmarks)
    print_table(*build_table(avg, pqtls))

if __name__ == '__main__':
    main()
