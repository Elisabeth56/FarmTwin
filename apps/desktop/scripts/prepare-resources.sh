#!/usr/bin/env bash
# Fills apps/desktop/resources/ with what the installer ships next to the shell:
#   api/       the FastAPI backend frozen by PyInstaller (no Python needed on the laptop)
#   llama/     llama-server from llama.cpp's official prebuilt release for this OS
#   embedder/  the search embedder, so search works offline from the first launch
#   whisper/   whisper-cli built from whisper.cpp source (no prebuilt binaries for Mac or Linux)
#
#   ./scripts/prepare-resources.sh <macos-arm64|macos-x64|ubuntu-x64|win-cpu-x64>
# LLAMA_TAG and WHISPER_TAG pick the llama.cpp and whisper.cpp versions; both are pinned so
# installers are reproducible.
set -euo pipefail
target="${1:?usage: prepare-resources.sh <macos-arm64|macos-x64|ubuntu-x64|win-cpu-x64>}"
here="$(cd "$(dirname "$0")/.." && pwd)"
api="$here/../api"
res="$here/resources"
rm -rf "$res" && mkdir -p "$res/api" "$res/llama" "$res/embedder" "$res/whisper"

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

echo "== whisper-cli"
wtag="${WHISPER_TAG:-v1.9.5}"
echo "whisper.cpp $wtag ($target)"
src="$(mktemp -d)"
git clone --quiet --depth 1 --branch "$wtag" https://github.com/ggml-org/whisper.cpp "$src"
# one static binary, CPU only; x86 builds need a CPU with AVX2 (most laptops from 2015 on)
flags=(-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_METAL=OFF
  -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_SERVER=OFF -DWHISPER_SDL2=OFF)
case "$target" in macos-arm64) ;; *) flags+=(-DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON) ;; esac
cmake -S "$src" -B "$src/build" "${flags[@]}" > /dev/null
cmake --build "$src/build" --config Release --target whisper-cli -j 4 > /dev/null
cli="$(find "$src/build" -type f \( -name whisper-cli -o -name whisper-cli.exe \) | head -1)"
cp "$cli" "$res/whisper/"
echo "$wtag" > "$res/whisper/WHISPER_TAG"

echo "== embedder"
(cd "$api" && FARMTWIN_EMBEDDER_DIR="$res/embedder" uv run python scripts/fetch_embedder.py)

du -sh "$res"/*
