#!/usr/bin/env bash
# Fills apps/desktop/resources/ with what the installer ships next to the shell:
#   api/       the FastAPI backend frozen by PyInstaller (no Python needed on the laptop)
#   llama/     llama-server from llama.cpp's official prebuilt release for this OS
#   embedder/  the search embedder, so search works offline from the first launch
#
#   ./scripts/prepare-resources.sh <macos-arm64|macos-x64|ubuntu-x64|win-cpu-x64>
# LLAMA_TAG picks the llama.cpp build; it is pinned so installers are reproducible. The tag used is printed.
set -euo pipefail
target="${1:?usage: prepare-resources.sh <macos-arm64|macos-x64|ubuntu-x64|win-cpu-x64>}"
here="$(cd "$(dirname "$0")/.." && pwd)"
api="$here/../api"
res="$here/resources"
rm -rf "$res" && mkdir -p "$res/api" "$res/llama" "$res/embedder"

echo "== backend"
(cd "$api" && uv sync --frozen --quiet && uv run pyinstaller farmtwin-api.spec --noconfirm --log-level WARN)
cp -R "$api/dist/farmtwin-api/." "$res/api/"

echo "== llama-server"
# llama.cpp's "latest" release is a source-only vX.Y.Z tag; the prebuilt binaries are on the bNNNN tags
tag="${LLAMA_TAG:-b11669}"
echo "llama.cpp $tag ($target)"
tmp="$(mktemp -d)"
gh release download "$tag" -R ggml-org/llama.cpp -D "$tmp" -p "llama-$tag-bin-$target.zip" -p "llama-$tag-bin-$target.tar.gz"
archive="$(ls "$tmp"/llama-* | head -1)"
case "$archive" in
  *.zip) (cd "$api" && uv run python -m zipfile -e "$archive" "$tmp/x") ;;  # unzip isn't on every runner
  *) mkdir -p "$tmp/x" && tar -xzf "$archive" -C "$tmp/x" ;;
esac
server="$(find "$tmp/x" -type f \( -name llama-server -o -name llama-server.exe \) | head -1)"
# llama-server needs the shared libraries that sit next to it in the archive
cp -R "$(dirname "$server")/." "$res/llama/"
chmod +x "$res/llama/"llama-server* || true
echo "$tag" > "$res/llama/LLAMA_TAG"

echo "== embedder"
(cd "$api" && FARMTWIN_EMBEDDER_DIR="$res/embedder" uv run python scripts/fetch_embedder.py)

du -sh "$res"/*
