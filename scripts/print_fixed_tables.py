#!/usr/bin/env python3
import sys
import os
import re
from collections import defaultdict as ddict
try:
    from tabulate import tabulate
except ImportError:
    print("tabulate is not installed. Please do a `pip install tabulate`.")
    sys.exit(1)
import random


BENCHMARK_FILE_RE = r"([A-z0-9]+)_([A-z0-9]+)_([A-z0-9]+)_([0-9]+).txt"
DESIRED_BENCHMARKS = [
    "rom_size_wolfssl",
#     "rom_size_PQClean",
    "rom_size_PQM4",
    "rom_size_ca_cert",
    "rom_size_PQM4_calculated",
    "elf_text_size",
    "peak_mem",
    "bytes_send",
    "bytes_received",
    "cycles_wc_pq_make_keypair",
    "cycles_wc_pq_kem_dec",
    "cycles_wc_pq_verify_hash",
    "cycles_wc_pq_kem_encapsulate",
    "cycles_connect_1mbit_13msdelay",
    "cycles_connect_1mbit_60msdelay",
    "cycles_connect_46kbit_1500msdelay",
    "cycles_send_1mbit_13msdelay",
    "cycles_recv_1mbit_13msdelay",
    "cycles_send_1mbit_60msdelay",
    "cycles_recv_1mbit_60msdelay",
    "cycles_send_46kbit_1500msdelay",
    "cycles_recv_46kbit_1500msdelay",
]

PQTLS_BENCHMARK_FILE_RE = r"([A-z0-9]+)_([A-z0-9]+)_([A-z0-9]+)_([0-9]+).txt"
PQTLS_DESIRED_BENCHMARKS = [
    "rom_size_wolfssl",
    # "rom_size_PQClean",
    "rom_size_PQM4",
    "rom_size_ca_cert",
    "rom_size_PQM4_calculated",
    "elf_text_size",
    "peak_mem",
    "bytes_send",
    "bytes_received",
    "cycles_wc_pq_make_keypair",
    "cycles_wc_pq_kem_dec",
    "cycles_wc_pq_verify_hash_0",
    "cycles_wc_pq_verify_hash_1",
    "cycles_connect_1mbit_13msdelay",
    "cycles_connect_1mbit_60msdelay",
    "cycles_connect_46kbit_1500msdelay",
    "cycles_send_1mbit_13msdelay",
    "cycles_recv_1mbit_13msdelay",
    "cycles_send_1mbit_60msdelay",
    "cycles_recv_1mbit_60msdelay",
    "cycles_send_46kbit_1500msdelay",
    "cycles_recv_46kbit_1500msdelay"
]

PQTLS_PAPER_TABLE1 = [
    "rom_size_PQM4_calculated",
    "pqm4_code_percent",
    "rom_size_ca_cert",
    "certificate_percent",
    "wolfssl_max_mem_usage"
]

PQTLS_PAPER_TABLE2 = [
    "bytes_traffic",
    "cycles_connect_1mbit_13msdelay",
    "handshake_cycles_spend_in_pqm4_1mbit_13msdelay",
    "cycles_connect_1mbit_60msdelay",
    "handshake_cycles_spend_in_pqm4_1mbit_60msdelay",
    "cycles_connect_46kbit_1500msdelay",
    "handshake_cycles_spend_in_pqm4_46kbit_1500msdelay",
]


# This is the .text section of our binary if there is no PQC included
KEMTLS_TEXT_BASE_SIZE = 180864
PQTLS_TEXT_BASE_SIZE = 185568

# Taken from https://github.com/mupq/pqm4/blob/master/benchmarks.md

STACK_BENCHMARKS = {
    "kyber512": {
        "wc_pq_make_keypair_stack": 4272,
        "wc_pq_kem_dec_stack": 5384,
        "wc_pq_kem_enc_stack": 5376
    },
    "lightsaber": {
        "wc_pq_make_keypair_stack": 5612,
        "wc_pq_kem_dec_stack": 6292,
        "wc_pq_kem_enc_stack": 6284
    },
    "ntruhps2048509": {
        "wc_pq_make_keypair_stack": 21344,
        "wc_pq_kem_dec_stack": 14800,
        "wc_pq_kem_enc_stack": 14060
    },
    "dilithium2": {
        "verify_hash_stack": 36188
    },
    "falcon512": {
        "verify_hash_stack": 388 + 39936 # Scratch buffer in .bss is huge
    },
    # From https://kannwischer.eu/papers/2021_rainbowm4.pdf
    "rainbowIclassic": {
        "verify_hash_stack": 812
    }
}

RAINBOW_PK_SIZE = 161600




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
                cert_root_alg, cert_leaf_alg, kex_alg, testcase_num = re.findall(PQTLS_BENCHMARK_FILE_RE, fname)[0]
            else:
                kex_alg, cert_sig_alg, cert_kem_alg, testcase_num = re.findall(BENCHMARK_FILE_RE, fname)[0]
        except IndexError:
            log(f"Filename doesn't fullfil regex, ignoring: {fname}")
            continue

        benchmarks = read_benchmark_file(os.path.join(path, fname))

        if benchmarks["CMD_finish_success"] != "y":
            raise ValueError(f"Benchmark in file {fname} did not run successfully! Exiting!")

        if pqtls:
            stack_usage_0 = STACK_BENCHMARKS[cert_root_alg]["verify_hash_stack"]
            stack_usage_1 = STACK_BENCHMARKS[cert_leaf_alg]["verify_hash_stack"]
            stack_usage_kex = max(
                STACK_BENCHMARKS[kex_alg]["wc_pq_make_keypair_stack"],
                STACK_BENCHMARKS[kex_alg]["wc_pq_kem_dec_stack"],
                STACK_BENCHMARKS[kex_alg]["wc_pq_kem_enc_stack"]
            )
            benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"]["wc_pq_verify_hash_0_stack"].append(stack_usage_0)
            benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"]["wc_pq_verify_hash_1_stack"].append(stack_usage_1)
            benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"]["kex_stack"].append(stack_usage_kex)

            if cert_root_alg == "rainbowIclassic" or cert_leaf_alg == "rainbowIclassic":
                benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"]["peak_mem"].append(RAINBOW_PK_SIZE)
        else:
            stack_usage_0 = STACK_BENCHMARKS[cert_sig_alg]["verify_hash_stack"]
            stack_usage_kex = max(
                STACK_BENCHMARKS[kex_alg]["wc_pq_make_keypair_stack"],
                STACK_BENCHMARKS[kex_alg]["wc_pq_kem_dec_stack"],
                STACK_BENCHMARKS[kex_alg]["wc_pq_kem_enc_stack"]
            )
            stack_usage_cert_kem = max(
                STACK_BENCHMARKS[cert_kem_alg]["wc_pq_make_keypair_stack"],
                STACK_BENCHMARKS[cert_kem_alg]["wc_pq_kem_dec_stack"],
                STACK_BENCHMARKS[cert_kem_alg]["wc_pq_kem_enc_stack"]
            )
            benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"]["wc_pq_verify_hash_stack"].append(stack_usage_0)
            benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"]["wc_pq_kem_stack"].append(stack_usage_cert_kem)
            benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"]["kex_stack"].append(stack_usage_kex)

            if cert_sig_alg == "rainbowIclassic":
                benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"]["peak_mem"].append(RAINBOW_PK_SIZE)

        for name, val in benchmarks.items():
            if name == "elf_text_size":
                # Find PQM4 size, including ASM, by comapring to binary without PQM4
                if pqtls:
                    benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"]["rom_size_PQM4_calculated"].append(val - PQTLS_TEXT_BASE_SIZE)
                else:
                    benchmarks_collected[f"{kex_alg}_{cert_sig_alg}_{cert_kem_alg}"]["rom_size_PQM4_calculated"].append(val - KEMTLS_TEXT_BASE_SIZE)

            if pqtls:
                benchmarks_collected[f"{kex_alg}_{cert_root_alg}_{cert_leaf_alg}"][name].append(val)
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
    if num < 1:
        return round(num * 100, 1), "%"

    if num > 10**6:
        return round(num / 10**6, 2), "*10^6"
    if num > 10**3:
        return round(num / 10**3, 2), "*10^3"
    return num, ""

def build_table(averaged_bench, desired_benchmarks, round_res=True):
    des_b = desired_benchmarks
    field_names = ["Algorithm Comb."] + des_b

    rows = []

    for comb in averaged_bench:
        row = [comb]
        for bname in des_b:
            if round_res:
                num, unit = round_bignum(averaged_bench[comb][bname])
                val = f"{num} {unit}"
            else:
                val = averaged_bench[comb][bname]
            row.append(val)
        rows.append(row)

    return field_names, rows

def print_table(field_names, rows, csv=False, format="pretty"):
    if csv:
        table = [",".join(field_names),]
        for row in rows:
            fields = []
            for f in row:
                if isinstance(f, float):
                    fields.append(str(int(f)))
                else:
                    fields.append(f)
            table.append(",".join(fields))
        table = "\n".join(table)
    else:
        table = tabulate(rows, field_names, tablefmt=format)

    print(table)

def calc_additional_columns(benchmarks, pqtls):


    for alg_comb, bench in benchmarks.items():
        # Size of wolfssl without PQM4
        bench["rom_size_wolfssl_wo_pqm4"] = bench["rom_size_wolfssl"] - bench["rom_size_PQM4"] - bench["rom_size_ca_cert"]
        # wolfssl size, also with asm routines
        bench["rom_size_wolfssl_complete"] = bench["rom_size_wolfssl_wo_pqm4"] + bench["rom_size_PQM4_calculated"]
        # Percent Size of PQM4 in Wolfssl 
        bench["pqm4_code_percent"] = bench["rom_size_PQM4_calculated"] / bench["rom_size_wolfssl_complete"]
        # Percent Size of Cert in Wolfssl 
        bench["certificate_percent"] = bench["rom_size_ca_cert"] / bench["rom_size_wolfssl_complete"]
        bench["bytes_traffic"] = bench["bytes_send"] + bench["bytes_received"]

        

        for name in ["1mbit_13msdelay", "1mbit_60msdelay", "46kbit_1500msdelay",]:
            bname = "handshake_cycles_spend_in_pqm4" + "_" + name
            source_bname = "cycles_connect_" + name
            if not pqtls:
                bench["wolfssl_max_mem_usage"] = bench["peak_mem"] + max(bench["wc_pq_verify_hash_stack"], bench["kex_stack"], bench["wc_pq_kem_stack"])
                # Percent of how many percent of cycles are spend within PQM4
                bench[bname] = (bench["cycles_wc_pq_make_keypair"] + bench["cycles_wc_pq_kem_dec"] + bench["cycles_wc_pq_verify_hash"] + bench["cycles_wc_pq_kem_encapsulate"]) / bench[source_bname] 
            else:
                bench["wolfssl_max_mem_usage"] = bench["peak_mem"] + max(bench["wc_pq_verify_hash_0_stack"], bench["wc_pq_verify_hash_1_stack"], bench["kex_stack"])
                
                bench[bname] = (bench["cycles_wc_pq_make_keypair"] + bench["cycles_wc_pq_kem_dec"] + bench["cycles_wc_pq_verify_hash_0"] + bench["cycles_wc_pq_verify_hash_1"]) / bench[source_bname]



def main():
    if len(sys.argv) < 2:
        log(f"Error, missing argument. Call: {sys.argv[0]} BENCHMARKS_DIR")
        sys.exit(1)

    # Wow, I'm lazy today... Well, my head hurts...
    pqtls = "--pqtls" in sys.argv
    csv = "--csv" in sys.argv
    paper_tables = "--paper" in sys.argv
    latex = "--latex" in sys.argv
    benchmarks = get_benchmarks(sys.argv[1], pqtls)

    avg = build_average(benchmarks)
    calc_additional_columns(avg, pqtls)

    format = "latex" if latex else "pretty"

    if not paper_tables:
        # Dont round for csv output
        des_bench = PQTLS_DESIRED_BENCHMARKS if pqtls else DESIRED_BENCHMARKS
        round_res = not csv
        field_names, rows = build_table(avg, des_bench, round_res)
        print_table(field_names, rows, csv, format)
    else:
        round_res = True
        field_names, rows = build_table(avg, PQTLS_PAPER_TABLE1, round_res)
        print_table(field_names, rows, csv, format)

        field_names, rows = build_table(avg, PQTLS_PAPER_TABLE2, round_res)
        print_table(field_names, rows, csv, format)
    



if __name__ == '__main__':
    main()
