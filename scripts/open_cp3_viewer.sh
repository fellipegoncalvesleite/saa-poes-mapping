#!/usr/bin/env bash
# Compatibility launcher; the CP3 figure page is now the interactive scientific viewer.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/scripts/open_viewer.sh"
