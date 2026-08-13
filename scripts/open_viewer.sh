#!/usr/bin/env bash
# Open the static scientific viewer in the default browser (macOS or Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIEWER="$ROOT/outputs/viewer/index.html"

if [ ! -f "$VIEWER" ]; then
  echo "Viewer not found: $VIEWER" >&2
  exit 1
fi

echo "Opening $VIEWER"
case "$(uname -s)" in
  Darwin)
    open "$VIEWER"
    ;;
  Linux)
    if ! command -v xdg-open >/dev/null 2>&1; then
      echo "xdg-open is required on Linux; open this file manually: $VIEWER" >&2
      exit 1
    fi
    xdg-open "$VIEWER" >/dev/null 2>&1 &
    ;;
  *)
    echo "Unsupported platform; open this file manually: $VIEWER" >&2
    exit 1
    ;;
esac
