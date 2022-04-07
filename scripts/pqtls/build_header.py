#!/usr/bin/env python3
import base64
import sys
import os
import textwrap

SIG_SCHEMES = [
    "dilithium2",
    "falcon512",
    "rainbowIclassic"
]

KEX_SCHEMES = [
    "kyber512",
    "lightsaber",
    "ntruhps2048509"
]


CERTIFICATE_PATH = "OQS/certs"
TEMPLATE_PATH = "scripts/templates/pqtls_experiment.h"
CERT_TEMPLATE_PATH = "scripts/templates/pqtls_ca.h"
ZEPHYR_PROJ_DIR = "zephyr-docker/zephyr_workspaces/pqtls-experiment/modules/crypto/wolfssl/"
TARGET_HEADER_PATH = os.path.join(ZEPHYR_PROJ_DIR, "wolfssl", "pqtls_experiment.h")
CERT_TARGET_HEADER_PATH = os.path.join(ZEPHYR_PROJ_DIR, "zephyr", "pqtls_ca.h")

PATHS_TO_CHECK = [
    CERTIFICATE_PATH,
    TEMPLATE_PATH,
    CERT_TEMPLATE_PATH,
    ZEPHYR_PROJ_DIR
]

MAX_LINE_WIDTH = 80


def bytes_to_hex_bytes(b: bytes):
    string = ", ".join(["0x{:02x}".format(c) for c in b])
    return "\n".join(textwrap.wrap(string, MAX_LINE_WIDTH))


def cert_to_hex_bytes(testcase_fname):
    with open(testcase_fname) as f:
        content = f.readlines()
        # Remove header and footer line (---- [...] ----)
        content_stripped = "".join(content[1:-1])
        content_decoded = base64.b64decode(content_stripped)
        return len(content_decoded), bytes_to_hex_bytes(content_decoded)


def fill_template(template_path, **kwargs):
    content = open(template_path).read()

    for k in kwargs:
        content = content.replace(f"${k}$", str(kwargs[k]))

    return content


def overwrite_header(template_path, header_path, **template_vars):
    if os.path.isfile(header_path):
        print(f"Path {header_path} already exists! Will overwrite!")

    content = fill_template(template_path, **template_vars)

    with open(header_path, "w") as f:
        f.write(content)

def check_path_exists_crash(path):
    if not os.path.exists(path):
        sys.stderr.write(f"Path {path} does not exist!")
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(f"Not enough arguments submitted. Do a: {sys.argv[0]} EPH_KEX_ALG CERT_SIG_ALG TESTCASE_NUMBER")
        sys.exit(1)

    for path in PATHS_TO_CHECK:
        check_path_exists_crash(path)

    eph_kex_alg = sys.argv[1]
    cert_sig_alg = sys.argv[2]
    testcase_num = int(sys.argv[3])

    testcase_path = os.path.join(CERTIFICATE_PATH, f"{cert_sig_alg}_{testcase_num:04d}_ca.crt")

    print("Using", testcase_path)

    check_path_exists_crash(testcase_path)

    ca_cert_len, ca_cert_hex = cert_to_hex_bytes(testcase_path)

    overwrite_header(
            TEMPLATE_PATH, TARGET_HEADER_PATH,
            eph_kex_alg=eph_kex_alg, cert_sig_alg=cert_sig_alg
    )

    overwrite_header(
            CERT_TEMPLATE_PATH, CERT_TARGET_HEADER_PATH,
            ca_cert_len=ca_cert_len, ca_cert_hex=ca_cert_hex
    )


if __name__ == '__main__':
    main()
