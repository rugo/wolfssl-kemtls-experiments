#!/bin/bash

set -o nounset
set -o errexit

echo "Generating KEMTLS certificates. This will take a long time."
scripts/generate_certificates.sh

echo "Generating PQTLS certificates. This will take a long time."
scripts/pqtls/generate_certificates.sh

echo "Starting KEMTLS experiments."
scripts/run_experiments.sh

echo "Starting PQTLS experiments."
scripts/pqtls/run_experiments.sh
