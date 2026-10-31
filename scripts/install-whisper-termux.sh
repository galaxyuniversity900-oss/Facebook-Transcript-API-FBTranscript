#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="${FBTRANSCRIPT_WHISPER_DIR:-$HOME/whisper.cpp}"
MODEL_DIR="${FBTRANSCRIPT_MODEL_DIR:-$HOME/.cache/fbtranscript}"
MODEL="$MODEL_DIR/ggml-tiny.bin"

echo "[1/4] Installing native build and audio tools..."
pkg update -y
pkg install -y git cmake clang make ffmpeg

echo "[2/4] Getting official whisper.cpp source..."
if [ -d "$ROOT/.git" ]; then
  git -C "$ROOT" pull --ff-only
else
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$ROOT"
fi

echo "[3/4] Building whisper-cli..."
cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON
cmake --build "$ROOT/build" --config Release -j2 --target whisper-cli
BIN="$ROOT/build/bin/whisper-cli"
if [ ! -x "$BIN" ]; then
  echo "Build did not produce $BIN" >&2
  exit 1
fi
ln -sf "$BIN" "$PREFIX/bin/whisper-cli"

echo "[4/4] Downloading multilingual tiny model..."
mkdir -p "$MODEL_DIR"
if [ ! -s "$MODEL" ]; then
  (cd "$ROOT" && bash ./models/download-ggml-model.sh tiny)
  if [ ! -s "$ROOT/models/ggml-tiny.bin" ]; then
    echo "Whisper model download failed." >&2
    exit 1
  fi
  cp "$ROOT/models/ggml-tiny.bin" "$MODEL"
fi

echo "Whisper CLI: $(command -v whisper-cli)"
echo "Model: $MODEL"
echo "Native speech recognition is ready. Restart FBTranscript before use."
