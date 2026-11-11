#!/usr/bin/env bash
# Fails if app code hardcodes user folders, ports or origins that belong in app/config.py.
set -euo pipefail
cd "$(dirname "$0")/.."
if grep -rnE '/Users/|/home/[a-z]|C:\\\\Users|localhost:[0-9]+|127\.0\.0\.1:[0-9]+|farmtwin\.db"' app --include='*.py' | grep -v '^app/config.py'; then
  echo "Hardcoded path, port or origin found above. Move it to app/config.py." >&2
  exit 1
fi
echo "No hardcoded paths."
