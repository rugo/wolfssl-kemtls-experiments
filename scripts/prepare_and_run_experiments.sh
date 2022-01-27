#!/bin/bash

set -o nounset
set -o errexit

echo "Generating certificates. This will take a long time."
scripts/generate_certificates.sh

echo "Starting experiments."
scripts/run_experiments.sh
