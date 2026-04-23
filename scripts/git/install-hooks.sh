#!/usr/bin/env bash
# Install findata-br git hooks by pointing `core.hooksPath` at .githooks/.
# Idempotent — run again to refresh symlinks / permissions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${SCRIPT_DIR}/guardrails.sh"

guardrails_install_hooks
