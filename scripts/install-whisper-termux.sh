#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

# Opt-in native whisper.cpp installer for Termux.
# No pkg update/upgrade and no automatic package installation.
ROOT="${FBTRANSCRIPT_WHISPER_DIR:-$HOME/whisper.cpp}"
MODEL_DIR="${FBTRANSCRIPT_MODEL_DIR:-$HOME/.cache/fbtranscript}"
MODEL="$MODEL_DIR/ggml-tiny.bin"
BIN="$ROOT/build/bin/whisper-cli"
THREADS="${FBTRANSCRIPT_BUILD_JOBS:-2}"

missing=()
for cmd in git cmake clang make ffmpeg; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1 && ! command -v wget2 >/dev/null 2>&1; then
  missing+=("curl or wget")
fi
if (("${#missing[@]}" > 0)); then
  echo "Missing tools: ${missing[*]}" >&2
  echo "No packages were installed. Install only the missing tools when you have Wi-Fi." >&2
  echo "Typical command: pkg install git cmake clang make ffmpeg curl" >&2
  exit 1
fi

# Termux shared-library search path (also used by FFmpeg subprocesses).
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$MODEL_DIR"

if [[ ! -d "$ROOT/.git" ]]; then
  if [[ -e "$ROOT" ]]; then
    echo "Refusing to overwrite existing non-git directory: $ROOT" >&2
    exit 1
  fi
  echo "[1/3] Cloning whisper.cpp source (shallow clone; no package upgrades)..."
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$ROOT"
else
  echo "[1/3] Reusing existing whisper.cpp source; no git pull."
fi

if [[ ! -x "$BIN" ]]; then
  echo "[2/3] Building whisper-cli for Android ARM64..."
  cmake -S "$ROOT" -B "$ROOT/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=ON \
    -DWHISPER_BUILD_TESTS=OFF \
    -DWHISPER_BUILD_EXAMPLES=ON \
    -DWHISPER_BUILD_SERVER=OFF
  cmake --build "$ROOT/build" --config Release --target whisper-cli --parallel "$THREADS"
fi

if [[ ! -x "$BIN" ]]; then
  echo "Build did not produce executable: $BIN" >&2
  exit 1
fi

if [[ -f "$MODEL" ]]; then
  size="$(wc -c < "$MODEL" | tr -d ' ')"
  if (( size < 50000000 )); then
    echo "Existing model appears incomplete ($size bytes): $MODEL" >&2
    echo "It was left untouched; no replacement was downloaded." >&2
    exit 1
  fi
  echo "[3/3] Reusing existing multilingual tiny model."
else
  echo "[3/3] Downloading multilingual tiny model (approximately 75 MB)..."
  temp_model_dir="$(mktemp -d "$MODEL_DIR/.tiny-download.XXXXXX")"
  cleanup() { rm -rf "$temp_model_dir"; }
  trap cleanup EXIT
  bash "$ROOT/models/download-ggml-model.sh" tiny "$temp_model_dir"
  downloaded="$temp_model_dir/ggml-tiny.bin"
  if [[ ! -s "$downloaded" ]] || (( $(wc -c < "$downloaded") < 50000000 )); then
    echo "Model download is incomplete; no model was installed." >&2
    exit 1
  fi
  mv "$downloaded" "$MODEL"
fi

mkdir -p "$PREFIX/bin"
ln -sf "$BIN" "$PREFIX/bin/whisper-cli"

echo
echo "Installation complete."
echo "Binary: $PREFIX/bin/whisper-cli"
echo "Model:  $MODEL"
echo "Test:   whisper-cli --help"
echo "Restart FBTranscript before transcribing."
