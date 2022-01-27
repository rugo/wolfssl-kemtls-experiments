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


CERTIFICATE_PATH = "kemtls-server-reproducible/certs"
TEMPLATE_PATH = "scripts/templates/kemtlsexperiments.h"
ZEPHYR_PROJ_DIR = "zephyr-docker/zephyr_workspaces/kemtls-experiment/modules/crypto/wolfssl/zephyr"
TARGET_HEADER_PATH = os.path.join(ZEPHYR_PROJ_DIR, "kemtlsexperiments.h")

PATHS_TO_CHECK = [
    CERTIFICATE_PATH,
    TEMPLATE_PATH,
    ZEPHYR_PROJ_DIR
]

MAX_LINE_WIDTH = 80


def bytes_to_hex_bytes(b: bytes):
    string = ", ".join(["0x{:02x}".format(c) for c in b])
    return "\n".join(textwrap.wrap(string, MAX_LINE_WIDTH))


def cert_to_hex_bytes(testcase_fname):
    with open(testcase_fname, "rb") as f:
        content = f.read()
        return len(content), bytes_to_hex_bytes(content)


def fill_template(template_path, **kwargs):
    content = open(template_path).read()

    for k in kwargs:
        content = content.replace(f"${k}$", str(kwargs[k]))
    
    return content


def check_path_exists_crash(path):
    if not os.path.exists(path):
        sys.stderr.write(f"Path {path} does not exist!")
        sys.exit(1)


def main():
    if len(sys.argv) < 5:
        sys.stderr.write("Not enough arguments submitted. Do a: {sys.argv[0]} EPH_KEX_ALG CERT_ROOT_SIG_ALG CERT_KEM_ALG TESTCASE_NUMBER")
        sys.exit(1)
    
    for path in PATHS_TO_CHECK:
        check_path_exists_crash(path)
    
    eph_kex_alg = sys.argv[1]
    cert_sig_alg = sys.argv[2]
    cert_kem_alg = sys.argv[3]
    testcase_num = int(1)

    testcase_path = os.path.join(CERTIFICATE_PATH, f"{cert_sig_alg}_{cert_kem_alg}_{testcase_num:04d}_ca.crt")
    
    check_path_exists_crash(testcase_path)
    
    ca_cert_len, ca_cert_hex = cert_to_hex_bytes(testcase_path)

    if os.path.isfile(TARGET_HEADER_PATH):
        print(f"Path {TARGET_HEADER_PATH} already exists! Will overwrite!")
    
    content = fill_template(
            TEMPLATE_PATH, eph_kex_alg=eph_kex_alg, 
            cert_sig_alg=cert_sig_alg, cert_kem_alg=cert_kem_alg, 
            ca_cert_len=ca_cert_len, ca_cert_hex=ca_cert_hex
    )

    with open(TARGET_HEADER_PATH, "w") as f:
        f.write(content)
    

if __name__ == '__main__':
    main()