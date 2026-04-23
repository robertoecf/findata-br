#!/usr/bin/env bash
# Local dev server with hot reload.
set -euo pipefail
cd "$(dirname "$0")/.."
exec findata serve --reload "$@"
