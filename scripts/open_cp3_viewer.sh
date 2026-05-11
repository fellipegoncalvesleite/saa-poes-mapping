#!/usr/bin/env bash
# Open the CP3 local HTML viewer (static page of existing figures) in the default browser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIEWER="$ROOT/outputs/viewer/index.html"

if [ ! -f "$VIEWER" ]; then
  echo "Viewer not found: $VIEWER" >&2
  exit 1
fi

echo "Opening $VIEWER"
xdg-open "$VIEWER" >/dev/null 2>&1 &
