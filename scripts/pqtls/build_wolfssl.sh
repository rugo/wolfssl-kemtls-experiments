#!/bin/bash

set -o nounset
set -o errexit

./scripts/build_wolfssl.sh --pqtls $@