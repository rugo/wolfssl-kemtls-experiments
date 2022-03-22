#ifndef WOLFSSL_KEMTLS_CA_H
#define WOLFSSL_KEMTLS_CA_H

#include "kemtlsexperiments.h"

#if defined(KEMTLS_CERT_ROOT_SIG_$cert_sig_alg$) && defined(KEMTLS_CERT_KEM_$cert_kem_alg$)
const char ca_cert[] = {
$ca_cert_hex$
};
int ca_cert_len = $ca_cert_len$;
#else
    #error "Certificate and configured SIG/KEM mismatch!"
#endif

#endif //WOLFSSL_KEMTLS_CA_H
