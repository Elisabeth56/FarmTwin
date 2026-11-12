#!/bin/sh
# lets the API supervise the fake model like a real llama-server binary (dev only)
exec "$(dirname "$0")/../.venv/bin/python" "$(dirname "$0")/fake_llama.py" "$@"
