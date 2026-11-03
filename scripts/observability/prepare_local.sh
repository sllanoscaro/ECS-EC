#!/usr/bin/env bash
# Prepare environment-scoped TLS/mTLS outside Git; see prepare_local.py for the contract.
set -euo pipefail
exec python3 "$(dirname "$0")/prepare_local.py" "$@"
