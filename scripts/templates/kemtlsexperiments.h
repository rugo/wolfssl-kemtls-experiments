#ifndef WOLFSSL_KEMTLSEXPERIMENTS_H
#define WOLFSSL_KEMTLSEXPERIMENTS_H

#define KEMTLS_CERT_ROOT_SIG_$cert_sig_alg$
#define KEMTLS_CERT_KEM_$cert_kem_alg$
#define KEMTLS_EPH_KEX_$eph_kex_alg$


#ifdef KEMTLS_EPH_KEX_lightsaber
#define KEX_GROUP PQ_LIGHTSABER
#endif

#ifdef KEMTLS_EPH_KEX_kyber512
#define KEX_GROUP PQ_KYBER512
#endif

#ifdef KEMTLS_EPH_KEX_ntruhps2048509
#define KEX_GROUP PQ_NTRUHPS2048509
#endif

#endif //WOLFSSL_KEMTLSEXPERIMENTS_H
