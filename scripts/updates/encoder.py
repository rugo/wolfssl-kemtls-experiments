import asn1
from datetime import datetime, timedelta
import subprocess
import base64
from io import BytesIO
import sys
import os
import resource
import time
import shutil


DEBUG = False

HOSTNAMES = list(
    map(lambda x: x.encode(), os.environ.get("HOSTNAMES", "servername").split(","))
)

subenv = os.environ.copy()
if "RUST_MIN_STACK" not in subenv:
    subenv["RUSTFLAGS"] = "-C target-cpu=native"
    subenv["RUST_MIN_STACK"] = str(20 * 1024 * 1024)


resource.setrlimit(
    resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
)

from algorithms import kems, signs, get_oid, get_oqs_id, is_sigalg


def public_key_der(algorithm, pk):
    encoder = asn1.Encoder()
    encoder.start()
    write_public_key(encoder, algorithm, pk)
    return encoder.output()


def private_key_der(algorithm, sk):
    encoder = asn1.Encoder()
    encoder.start()
    encoder.enter(asn1.Numbers.Sequence)
    encoder.write(0, asn1.Numbers.Integer)
    encoder.enter(asn1.Numbers.Sequence)  # AlgorithmIdentifier
    oid = get_oid(algorithm)
    encoder.write(oid, asn1.Numbers.ObjectIdentifier)
    #encoder.write(None)
    encoder.leave()  # AlgorithmIdentifier
    #nestedencoder = asn1.Encoder()
    #nestedencoder.start()
    #nestedencoder.write(sk, asn1.Numbers.OctetString)
    #encoder.write(nestedencoder.output(), asn1.Numbers.OctetString)
    encoder.write(sk, asn1.Numbers.OctetString)
    encoder.leave()
    return encoder.output()


def write_pem(filename, label, data):
    data = der_to_pem(data, label)
    with open(filename, "wb") as f:
        f.write(data)


def der_to_pem(data, label=b"CERTIFICATE"):
    buf = BytesIO()
    buf.write(b"-----BEGIN ")
    buf.write(label)
    buf.write(b"-----\n")

    base64buf = BytesIO(base64.b64encode(data))
    line = base64buf.read(64)
    while line:
        buf.write(line)
        buf.write(b"\n")
        line = base64buf.read(64)

    buf.write(b"-----END ")
    buf.write(label)
    buf.write(b"-----\n")
    return buf.getvalue()


def set_up_algorithm(algorithm, type):
    if type == "kem":
        set_up_kem_algorithm(algorithm)
    else:
        set_up_sign_algorithm(algorithm)


def set_up_sign_algorithm(algorithm):
    if algorithm != "XMSS":
        content = f"pub use oqs::sig::Algorithm::{get_oqs_id(algorithm)} as alg;"
        with open("signutil/src/lib.rs", "w") as f:
            f.write(content)


def set_up_kem_algorithm(algorithm):
    content = f"pub use oqs::kem::Algorithm::{get_oqs_id(algorithm)} as thealgorithm;"
    with open("kemutil/src/kem.rs", "w") as f:
        f.write(content)


def run_signutil(example, alg, *args):
    if alg.lower() == "xmss":
        cwd = "xmss-rs"
    else:
        cwd = "signutil"

    print(f"Running 'cargo run --example {example} {' '.join(args)}' in {cwd}")
    subprocess.run(
        [*"cargo run --release --example".split(), example, *args],
        cwd=cwd,
        check=True,
        capture_output=False,
        env=subenv,
    )


def get_keys(type, algorithm):
    if type == "kem":
        return get_kem_keys(algorithm)
    elif type == "sign":
        return get_sig_keys(algorithm)


def get_kem_keys(_):
    subprocess.run(
        ["cargo", "run", "--release"],
        cwd="kemutil",
        check=True,
        env=subenv,
        capture_output=True,
    )
    with open("kemutil/publickey.bin", "rb") as f:
        pk = f.read()
    with open("kemutil/secretkey.bin", "rb") as f:
        sk = f.read()
    return (pk, sk)


def get_sig_keys(alg):
    run_signutil("keygen", alg)
    if alg.lower() == "xmss":
        with open("xmss-rs/publickey.bin", "rb") as f:
            pk = f.read()
        with open("xmss-rs/secretkey.bin", "rb") as f:
            sk = f.read()
    else:
        with open("signutil/publickey.bin", "rb") as f:
            pk = f.read()
        with open("signutil/secretkey.bin", "rb") as f:
            sk = f.read()
    return (pk, sk)


def print_date(time):
    return time.strftime("%y%m%d%H%M%SZ").encode()


def write_public_key(encoder, algorithm, pk):
    encoder.enter(asn1.Numbers.Sequence)  # SubjectPublicKeyInfo
    encoder.enter(asn1.Numbers.Sequence)  # AlgorithmIdentifier
    # FIXME: This should be parameterized
    encoder.write(get_oid(algorithm), asn1.Numbers.ObjectIdentifier)
    #encoder.write(None)
    encoder.leave()  # AlgorithmIdentifier
    encoder.write(pk, asn1.Numbers.BitString)
    encoder.leave()


def write_signature(
    encoder,
    algorithm,
    sign_algorithm,
    pk,
    signing_key,
    is_ca,
    pathlen,
    subject,
    issuer,
    client_auth,
):
    tbsencoder = asn1.Encoder()
    tbsencoder.start()
    write_tbs_certificate(
        tbsencoder,
        algorithm,
        sign_algorithm,
        pk,
        is_ca=is_ca,
        pathlen=pathlen,
        subject=subject,
        issuer=issuer,
        client_auth=client_auth,
    )
    tbscertificate_bytes = tbsencoder.output()
    tbscertbytes_file = f"tbscertbytes_for{algorithm}_by_{signing_key[3:].lower()}.bin"
    tbssig_file = f"tbs_sig_for-{algorithm}-by-{signing_key[3:].lower()}.bin"
    with open(tbscertbytes_file, "wb") as f:
        f.write(tbscertificate_bytes)

    # Sign tbscertificate_bytes
    if DEBUG:
        time.sleep(2)
    run_signutil(
        "signer",
        sign_algorithm,
        signing_key.lower(),
        f"../{tbscertbytes_file}",
        f"../{tbssig_file}",
    )

    # Obtain signature
    with open(tbssig_file, "rb") as f:
        sig = f.read()

    # Write bytes as bitstring
    encoder.write(sig, asn1.Numbers.BitString)


def write_signature_algorithm(encoder, algorithm):
    encoder.enter(asn1.Numbers.Sequence)  # enter algorithmidentifier
    encoder.write(get_oid(algorithm), asn1.Numbers.ObjectIdentifier)
    # encoder.write(None)  # Parameters
    encoder.leave()  # Leave AlgorithmIdentifier


def write_tbs_certificate(
    encoder,
    algorithm,
    sign_algorithm,
    pk,
    is_ca=False,
    pathlen=4,
    subject="ThomCert",
    issuer="ThomCert",
    client_auth=False,
):
    #  TBSCertificate  ::=  SEQUENCE  {
    #      version         [0]  EXPLICIT Version DEFAULT v1,
    #      serialNumber         CertificateSerialNumber,
    #      signature            AlgorithmIdentifier,
    #      issuer               Name,
    #      validity             Validity,
    #      subject              Name,
    #      subjectPublicKeyInfo SubjectPublicKeyInfo,
    #      issuerUniqueID  [1]  IMPLICIT UniqueIdentifier OPTIONAL,
    #         -- If present, version MUST be v2 or v3
    #      subjectUniqueID [2]  IMPLICIT UniqueIdentifier OPTIONAL,
    #            -- If present, version MUST be v2 or v3
    #      extensions      [3]  EXPLICIT Extensions OPTIONAL
    #            -- If present, version MUST be v3
    #  }
    encoder.enter(asn1.Numbers.Sequence)
    encoder.enter(0, cls=asn1.Classes.Context)  # [0]
    encoder.write(2)  # version 3
    encoder.leave()  # [0]
    encoder.write(1)  # serialnumber

    write_signature_algorithm(encoder, sign_algorithm)

    # ISSUER
    encoder.enter(asn1.Numbers.Sequence)  # Name
    encoder.enter(asn1.Numbers.Set)  # Set of attributes
    encoder.enter(asn1.Numbers.Sequence)
    encoder.write("2.5.4.3", asn1.Numbers.ObjectIdentifier)  # commonName
    encoder.write(issuer, asn1.Numbers.PrintableString)
    encoder.leave()  # commonName
    encoder.leave()  # Set
    encoder.leave()  # Name

    # Validity
    now = datetime.utcnow()
    encoder.enter(asn1.Numbers.Sequence)  # Validity
    encoder.write(print_date(now), asn1.Numbers.UTCTime)
    encoder.write(print_date(now + timedelta(days=9000)), asn1.Numbers.UTCTime)
    encoder.leave()  # Validity

    # Subject
    encoder.enter(asn1.Numbers.Sequence)  # Name
    if is_ca or client_auth:
        encoder.enter(asn1.Numbers.Set)  # Set of attributes
        encoder.enter(asn1.Numbers.Sequence)
        encoder.write("2.5.4.3", asn1.Numbers.ObjectIdentifier)  # commonName
        encoder.write(subject, asn1.Numbers.PrintableString)
        encoder.leave()  # commonName
        encoder.leave()  # Set
    encoder.leave()  # empty Name: use subjectAltName (critical!)

    # SubjectPublicKeyInfo
    #    SubjectPublicKeyInfo  ::=  SEQUENCE  {
    #      algorithm            AlgorithmIdentifier,
    #      subjectPublicKey     BIT STRING  }
    # print(f"Written {len(pk)} bytes of pk")
    write_public_key(encoder, algorithm, pk)

    # issuerUniqueId
    # skip?

    # Extensions
    encoder.enter(3, cls=asn1.Classes.Context)  # [3]
    encoder.enter(asn1.Numbers.Sequence)  # Extensions
    extvalue = asn1.Encoder()
    if not is_ca and not client_auth:
        encoder.enter(asn1.Numbers.Sequence)  # Extension 1
        encoder.write("2.5.29.17", asn1.Numbers.ObjectIdentifier)
        encoder.write(True, asn1.Numbers.Boolean)  # Critical
        extvalue.start()
        extvalue.enter(asn1.Numbers.Sequence)  # Sequence of names
        for name in HOSTNAMES:
            extvalue._emit_tag(0x02, asn1.Types.Primitive, asn1.Classes.Context)
            extvalue._emit_length(len(name))
            extvalue._emit(name)
        extvalue.leave()  # Sequence of names
        encoder.write(extvalue.output(), asn1.Numbers.OctetString)
        encoder.leave()  # Extension 1

    # Extended Key Usage
    if not is_ca:
        encoder.enter(asn1.Numbers.Sequence)  # Extension 2
        encoder.write("2.5.29.37", asn1.Numbers.ObjectIdentifier)
        encoder.write(False, asn1.Numbers.Boolean)  # Critical
        extvalue = asn1.Encoder()
        extvalue.start()
        extvalue.enter(asn1.Numbers.Sequence)  # Key Usages
        if client_auth:
            extvalue.write(
                "1.3.6.1.5.5.7.3.2", asn1.Numbers.ObjectIdentifier
            )  # clientAuth
        else:
            extvalue.write(
                "1.3.6.1.5.5.7.3.1", asn1.Numbers.ObjectIdentifier
            )  # serverAuth
        extvalue.leave()  # Key Usages
        encoder.write(extvalue.output(), asn1.Numbers.OctetString)
        encoder.leave()  # Extension 2

    encoder.enter(asn1.Numbers.Sequence)  # Extension CA
    encoder.write("2.5.29.19", asn1.Numbers.ObjectIdentifier)  # BasicConstr
    encoder.write(True, asn1.Numbers.Boolean)  # Critical
    extvalue = asn1.Encoder()
    extvalue.start()
    extvalue.enter(asn1.Numbers.Sequence)  # Constraints
    extvalue.write(is_ca, asn1.Numbers.Boolean)  # cA = True
    if is_ca:
        extvalue.write(pathlen, asn1.Numbers.Integer)  # Max path length
    extvalue.leave()  # Constraints
    encoder.write(extvalue.output(), asn1.Numbers.OctetString)
    encoder.leave()  # BasicConstraints

    encoder.leave()  # Extensions
    encoder.leave()  # [3]

    # Done
    encoder.leave()  # Leave TBSCertificate SEQUENCE


def generate(
    pk_algorithm,
    sig_algorithm,
    filename,
    signing_key,
    type="sign",
    ca=False,
    pathlen=4,
    subject="ThomCert",
    issuer="ThomCert",
    client_auth=False,
):
    filename = filename.lower()
    set_up_algorithm(pk_algorithm, type)

    (pk, sk) = get_keys(type, pk_algorithm)
    write_pem(f"{filename}.pub", b"PUBLIC KEY", public_key_der(pk_algorithm, pk))
    write_pem(f"{filename}.key", b"PRIVATE KEY", private_key_der(pk_algorithm, sk))
    with open(f"{filename}.pub.bin", "wb") as publickeyfile:
        publickeyfile.write(pk)
    with open(f"{filename}.key.bin", "wb") as secretkeyfile:
        secretkeyfile.write(sk)

    set_up_sign_algorithm(sig_algorithm)

    encoder = asn1.Encoder()
    encoder.start()

    # SEQUENCE of three things
    #   Certificate  ::=  SEQUENCE  {
    #       tbsCertificate       TBSCertificate,
    #       signatureAlgorithm   AlgorithmIdentifier,
    #       signatureValue       BIT STRING  }

    encoder.enter(asn1.Numbers.Sequence)  # Certificate
    write_tbs_certificate(
        encoder,
        pk_algorithm,
        sig_algorithm,
        pk,
        is_ca=ca,
        pathlen=pathlen,
        subject=subject,
        issuer=issuer,
        client_auth=client_auth,
    )
    # Write signature algorithm
    write_signature_algorithm(encoder, sig_algorithm)
    write_signature(
        encoder,
        pk_algorithm,
        sig_algorithm,
        pk,
        signing_key,
        is_ca=ca,
        pathlen=pathlen,
        subject=subject,
        issuer=issuer,
        client_auth=client_auth,
    )

    encoder.leave()  # Leave Certificate SEQUENCE

    with open(f"{filename}.crt.bin", "wb") as file_:
        file_.write(encoder.output())
    write_pem(f"{filename}.crt", b"CERTIFICATE", encoder.output())


def get_classic_certs():
    shutil.copyfile("rsas-int/x25519/x25519.pub", "kem.pub")
    shutil.copyfile("rsas-int/x25519/x25519.crt", "kem.crt")
    shutil.copyfile("rsas-int/x25519/x25519.chain.crt", "kem.chain.crt")
    shutil.copyfile("rsas-int/x25519/x25519.key", "kem.key")
    shutil.copyfile("rsas-int/pki/ca.crt", "signing-int.crt")
    shutil.copyfile("rsas-int/pki/ca.crt", "kem-int.crt")
    shutil.copyfile("rsas-root/pki/ca.crt", "signing-ca.crt")
    shutil.copyfile("rsas-root/pki/ca.crt", "kem-ca.crt")
    shutil.copyfile("rsas-int/pki/issued/servername.crt", "signing.crt")
    shutil.copyfile("rsas-int/pki/private/servername.key", "signing.key")
    shutil.copyfile("rsas-int/pki/ca.crt", "client-ca.crt")
    shutil.copyfile("rsas-int/pki/private/client.key", "client.key")
    shutil.copyfile("rsas-int/pki/issued/client.crt", "client.crt")
    with open("signing.chain.crt", "wb") as f:
        with open("signing.crt", "rb") as r:
            f.write(r.read())
        with open("signing-int.crt", "rb") as r:
            f.write(r.read())
    with open("signing.all.crt", "wb") as f:
        with open("signing.chain.crt", "rb") as r:
            f.write(r.read())
        with open("signing-ca.crt", "rb") as r:
            f.write(r.read())


if __name__ == "__main__":
    root_sign_algorithm = os.environ.get("ROOT_SIGALG", "dilithium2").lower()
    intermediate_sign_algorithm = os.environ.get("INT_SIGALG", "dilithium2").lower()
    leaf_auth_algorithm = os.environ.get("LEAF_ALG", "dilithium2").lower()
    client_alg = os.environ.get("CLIENT_ALG", None)
    client_sigalg = os.environ.get("CLIENT_CA_ALG", None)
    if leaf_auth_algorithm in ("x25519", "rsa2048"):
        get_classic_certs()
        print("not doing anything for x25519")
        sys.exit(0)

    assert is_sigalg(intermediate_sign_algorithm), intermediate_sign_algorithm
    assert is_sigalg(root_sign_algorithm), root_sign_algorithm
    assert client_sigalg is None or client_alg is not None

    print(f"Hostnames: {HOSTNAMES}")

    print(
        f"Generating keys for {leaf_auth_algorithm} signed by {intermediate_sign_algorithm} signed by {root_sign_algorithm}"
    )
    if is_sigalg(leaf_auth_algorithm):
        generate(
            root_sign_algorithm,
            root_sign_algorithm,
            "signing-ca",
            "../signing-ca.key.bin",
            type="sign",
            ca=True,
            subject="ThomCert CA",
            issuer="ThomCert CA",
        )
        generate(
            intermediate_sign_algorithm,
            root_sign_algorithm,
            "signing-int",
            "../signing-ca.key.bin",
            type="sign",
            ca=True,
            pathlen=1,
            subject="ThomCert Int CA",
            issuer="ThomCert CA",
        )
        generate(
            leaf_auth_algorithm,
            intermediate_sign_algorithm,
            "signing",
            "../signing-int.key.bin",
            type="sign",
            ca=False,
            issuer="ThomCert Int CA",
            subject="",
        )

        with open("signing.chain.crt", "wb") as f:
            with open("signing.crt", "rb") as r:
                f.write(r.read())
            with open("signing-int.crt", "rb") as r:
                f.write(r.read())
        with open("signing.all.crt", "wb") as f:
            with open("signing.crt", "rb") as r:
                f.write(r.read())
            with open("signing-int.crt", "rb") as r:
                f.write(r.read())
            with open("signing-ca.crt", "rb") as r:
                f.write(r.read())
    else:
        print("KEM Certificate time")

        # KEM certs
        generate(
            root_sign_algorithm,
            root_sign_algorithm,
            "kem-ca",
            "../kem-ca.key.bin",
            type="sign",
            ca=True,
            issuer="ThomCert CA",
            subject="ThomCert CA",
        )
        # generate(
        #     intermediate_sign_algorithm,
        #     root_sign_algorithm,
        #     "kem-int",
        #     "../kem-ca.key.bin",
        #     type="sign",
        #     ca=True,
        #     pathlen=1,
        #     issuer="ThomCert CA",
        #     subject="ThomCert Int CA",
        # )
        print(f"Generating KEM cert for {leaf_auth_algorithm}")
        generate(
            leaf_auth_algorithm,
            root_sign_algorithm,
            f"kem",
            "../kem-ca.key.bin",
            type="kem",
            issuer="ThomCert CA",
        )

        with open(f"kem.chain.crt", "wb") as file_:
            with open(f"kem.crt", "rb") as r:
                file_.write(r.read())
            # with open("kem-int.crt", "rb") as r:
            #     file_.write(r.read())

    if client_alg:
        print("Generating client cert")
        client_alg = client_alg.lower()
        client_sigalg = client_sigalg.lower()
        assert is_sigalg(client_sigalg), client_sigalg

        generate(
            client_sigalg,
            client_sigalg,
            "client-ca",
            "../client-ca.key.bin",
            type="sign",
            ca=True,
            subject="ThomCert Client CA",
            issuer="ThomCert Client CA",
        )
        generate(
            client_alg,
            client_sigalg,
            "client",
            "../client-ca.key.bin",
            type=("sign" if is_sigalg(client_alg) else "kem"),
            ca=False,
            issuer="ThomCert Client CA",
            subject="client",
            client_auth=True,
        )
    else:
        print("No client auth necessary")
        print("client_alg:", client_alg)
