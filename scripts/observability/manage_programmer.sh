#!/usr/bin/env bash
# External Programador provision/revoke; credentials are requested exclusively through TTY.
set -euo pipefail
obs_repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$obs_repo_root/.venv/bin/python" "$obs_repo_root/scripts/observability/manage_programmer.py" "$@"
