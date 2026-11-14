#!/usr/bin/env bash
# Real-model checks on the target Mac: the answer eval, then the app for a hand check.
#
#   ./evals/run-on-mac.sh            # quick: 10 questions (about 15 minutes on the 2014 MacBook)
#   ./evals/run-on-mac.sh full       # all 51 questions (about an hour)
#   ./evals/run-on-mac.sh app        # skip the eval, just start the app with the real model
#
# Uses the v1 paths for llama-server and the model; override with LLAMA_SERVER=... MODEL=...
# Set GROQ_API_KEY to add the judge scores.
set -euo pipefail

LLAMA_SERVER="${LLAMA_SERVER:-$HOME/dev/tools/llama.cpp/build/bin/llama-server}"
MODEL="${MODEL:-$HOME/farmtwin-models/qwen2.5-3b-instruct-q4_k_m.gguf}"
cd "$(dirname "$0")/.."

for tool in uv pnpm git; do
  command -v "$tool" >/dev/null || { echo "Needs $tool. Install it, then run this again."; exit 1; }
done
[ -x "$LLAMA_SERVER" ] || { echo "No llama-server at $LLAMA_SERVER. Set LLAMA_SERVER=/path/to/llama-server"; exit 1; }
[ -f "$MODEL" ] || { echo "No model at $MODEL. Set MODEL=/path/to/model.gguf"; exit 1; }

echo "== installing dependencies"
(cd apps/api && uv sync --quiet)
pnpm install --silent

export FARMTWIN_LLAMA_SERVER_BIN="$LLAMA_SERVER"
export FARMTWIN_LLM_MODEL_PATH="$MODEL"

if [ "${1:-quick}" != "app" ]; then
  # anything else using the model or memory skews the numbers
  if pgrep -x llama-server >/dev/null; then
    echo "Another llama-server is running. Quit it first so the memory numbers are clean."; exit 1
  fi
  echo "== answer eval (FarmTwin starts and stops the model itself)"
  if [ "${1:-quick}" = "full" ]; then pnpm eval:answers; else pnpm eval:answers -- --sample 10; fi
  echo
  echo "== recording the website demo's answers with the real model"
  (cd apps/api && uv run python scripts/fetch_embedder.py && uv run python scripts/record_demo.py --answers)
  echo
  echo "Results are in evals/results/ and apps/web/src/demo/fixtures.json. Commit and push both."
fi

echo
echo "== preparing the app's search index"
(cd apps/api && uv run python scripts/fetch_embedder.py && uv run python scripts/ingest.py)

echo
echo "== starting the app with the real model"
echo "Open http://localhost:5173, choose 'Explore a sample farm' and ask a question."
echo "Check: progress shows at once, the answer streams, sources open, Stop works. Ctrl+C to quit."
pnpm dev
